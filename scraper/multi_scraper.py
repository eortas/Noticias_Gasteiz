import json
import os
import time
import re
import urllib.parse
from datetime import datetime, timedelta, timezone
import cloudscraper
from bs4 import BeautifulSoup
from textblob import TextBlob

class MultiScraper:
    def __init__(self):
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
            'Referer': 'https://www.google.com/'
        }
        self.data_output = "data/news.json"
        self.history_file = "scraper/history.json"
        self.news_data = []
        self.history = self._load_history()

    def _load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
            except:
                return set()
        return set()

    def _save_history(self):
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(list(self.history), f, indent=2, ensure_ascii=False)

    def run(self):
        print("Iniciando scraping múltiple...")
        
        # El Correo (Prioridad)
        try:
            self.scrape_el_correo()
        except Exception as e:
            print(f"Error El Correo: {e}")

        # Gasteiz Hoy (API WordPress + RSS)
        try:
            self.scrape_gasteiz_hoy()
        except Exception as e:
            print(f"Error Gasteiz Hoy: {e}")

        # Guardar resultados
        self._save_results()
        self._save_history()

    def _save_results(self):
        if not self.news_data:
            print("No hay noticias nuevas para guardar.")
            return

        # Cargar existentes para no duplicar por URL
        existing_news = []
        if os.path.exists(self.data_output):
            try:
                with open(self.data_output, 'r', encoding='utf-8') as f:
                    existing_news = json.load(f)
            except:
                existing_news = []

        seen_urls = {item['url'] for item in existing_news}
        seen_titles = set()
        seen_images = set()
        
        # Poblar títulos vistos (prefijo para normalizar)
        for item in existing_news:
            clean_t = item['title'].split('|')[0].split(' - ')[0].strip().lower()
            norm_t = "".join(filter(str.isalnum, clean_t))
            if norm_t[:60]: seen_titles.add(norm_t[:60])
            if item.get('image'): seen_images.add(item['image'])

        unique_news = existing_news.copy()
        
        for item in self.news_data:
            url = item['url']
            title = item['title']
            img_url = item.get('image')
            
            if url in seen_urls:
                continue

            clean_title = title.split('|')[0].split(' - ')[0].strip().lower()
            if ": " in clean_title[:15]:
                clean_title = clean_title.split(": ", 1)[1]
                
            norm_title = "".join(filter(str.isalnum, clean_title))
            title_prefix = norm_title[:60]
            
            # Solo deduplicamos por título si NO es Gasteiz Hoy
            if item.get('source') != 'Gasteiz Hoy' and title_prefix and title_prefix in seen_titles:
                continue

            unique_news.append(item)
            seen_urls.add(url)
            if img_url: seen_images.add(img_url)
            if title_prefix: seen_titles.add(title_prefix)

        # Filtro de 72 horas
        now = datetime.now(timezone.utc)
        limit_date = now - timedelta(hours=72)
        
        latest_news = []
        for item in unique_news:
            item_dt = self._parse_date(item.get('date', ''))
            if item_dt >= limit_date:
                latest_news.append(item)
        
        # Cap de seguridad de max 200
        latest_news = latest_news[:200]
        
        with open(self.data_output, 'w', encoding='utf-8') as f:
            json.dump(latest_news, f, indent=2, ensure_ascii=False)
        
        print(f"Scraping completado. Guardadas {len(latest_news)} noticias de las últimas 72h.")

    def _normalize_url(self, url):
        if '?' in url:
            return url.split('?')[0]
        return url

    def _get_og_image(self, soup):
        meta = soup.find('meta', property='og:image')
        if meta and meta.get('content'):
            return meta['content'].strip()
        return None

    def _get_ddg_proxy_url(self, original_url):
        if not original_url: return None
        try:
            encoded_url = urllib.parse.quote(original_url)
            return f"https://external-content.duckduckgo.com/iu/?u={encoded_url}"
        except:
            return original_url

    def scrape_el_correo(self):
        import hashlib
        import urllib.request
        import json
        url = "https://www.elcorreo.com/alava/araba/"
        print(f"Scrapeando El Correo: {url}")
        try:
            res = self.scraper.get(url, headers=self.headers, timeout=15)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                articles = soup.find_all('article')
                
                # Googlebot headers para saltar el muro de pago en artículos individuales
                gb_headers = {
                    'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
                }
                
                for art in articles[:15]:  # Limitamos a los 15 primeros para no saturar
                    link = art.find('a')
                    if not link or not link.get('href'): continue
                    
                    full_url = link['href']
                    if not full_url.startswith('http'):
                        full_url = "https://www.elcorreo.com" + full_url
                    
                    full_url = self._normalize_url(full_url)
                    if full_url in self.history: continue

                    title_el = art.find(['h2', 'h1', 'h3'])
                    title = title_el.get_text().strip() if title_el else ""
                    if not title: continue

                    # Filtros de exclusión
                    if any(x in title.lower() for x in ['el boulevard', 'publirreportaje', 'patrocinado']):
                        continue
                    if "/alava/" not in full_url and "/vitoria/" not in full_url:
                        continue

                    # Extraer cuerpo completo visitando el artículo con Googlebot
                    body_text = ""
                    try:
                        req = urllib.request.Request(full_url, headers=gb_headers)
                        with urllib.request.urlopen(req, timeout=10) as response:
                            html = response.read().decode('utf-8', errors='ignore')
                            
                            paragraphs = []
                            # Intento 1: Extraer desde el JSON-LD (articleBody)
                            ld_jsons = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
                            for ld in ld_jsons:
                                try:
                                    data = json.loads(ld)
                                    if isinstance(data, list):
                                        for item in data:
                                            if isinstance(item, dict) and 'articleBody' in item:
                                                paragraphs.extend(item['articleBody'].split('\n'))
                                    elif isinstance(data, dict):
                                        if 'articleBody' in data:
                                            paragraphs.extend(data['articleBody'].split('\n'))
                                except:
                                    pass
                                    
                            # Intento 2: Parsing HTML tradicional si no hay JSON-LD
                            if not paragraphs:
                                p_matches = re.findall(r'<(?:p|div)[^>]*class="[^"]*voc-p[^"]*"[^>]*>(.*?)</(?:p|div)>', html, re.DOTALL)
                                if not p_matches:
                                    p_matches = re.findall(r'<p.*?>(.*?)</p>', html, re.DOTALL)
                                
                                blacklist = ["©", "todos los derechos reservados", "vídeo es exclusivo", "disfruta de acceso", "inicia sesión", "temas", "comentarios", "suscríbete", "iniciar sesión"]
                                for p in p_matches:
                                    text = re.sub('<.*?>', '', p).strip()
                                    if len(text) > 40 and not any(b.lower() in text.lower() for b in blacklist):
                                        if not re.search(r'[.!?]$', text) and len(text.split()) < 20:
                                            continue
                                        paragraphs.append(text)
                            else:
                                paragraphs = [re.sub('<.*?>', '', p).strip() for p in paragraphs if len(p.strip()) > 30]
                                
                            if paragraphs:
                                body_text = "\n\n".join(paragraphs)
                    except Exception as e:
                        print(f"  Error obteniendo body de {full_url}: {e}")
                    
                    # Si falla la extracción completa, usar el subtítulo de la portada
                    if not body_text:
                        subtitle_el = art.find(['p', 'span'], class_=lambda c: c and any(x in (c if isinstance(c, str) else ' '.join(c)) for x in ['subtitle', 'summary', 'lead', 'entradilla', 'deck']))
                        body_text = subtitle_el.get_text().strip() if subtitle_el else title

                    # Generar ID único
                    article_id = hashlib.md5(full_url.encode()).hexdigest()[:10]

                    # Imagen
                    image = self._get_og_image(art) or self._get_ddg_proxy_url(art.find('img').get('src') if art.find('img') else None)

                    self.news_data.append({
                        'id': article_id,
                        'title': title,
                        'url': full_url,
                        'source': 'El Correo',
                        'body': body_text,
                        'date': datetime.now(timezone.utc).isoformat(),
                        'sentiment': 0,
                        'image': image
                    })
                    self.history.add(full_url)
                    time.sleep(1) # Pausa entre peticiones para evitar bloqueos
        except Exception as e:
            print(f"Error scraping El Correo: {e}")

    def scrape_gasteiz_hoy(self):
        print("Scrapeando Gasteiz Hoy (API WP + RSS + Portada)...")
        links_data = {}

        # 1. API WordPress
        try:
            api_url = "https://www.gasteizhoy.com/wp-json/wp/v2/posts?per_page=100&_embed"
            res = self.scraper.get(api_url, headers=self.headers, timeout=15)
            if res.status_code == 200:
                posts = res.json()
                for post in posts:
                    url = post.get('link', '')
                    if not url: continue
                    
                    # FILTRO: Evitar sección comercios y patrocinados
                    if "/comercios/" in url.lower() or "el-boulevard" in url.lower():
                        continue
                        
                    title = post.get('title', {}).get('rendered', '')
                    title = BeautifulSoup(title, "html.parser").get_text()
                    
                    if any(x in title.lower() for x in ['el boulevard', 'publirreportaje', 'patrocinado']):
                        continue

                    body_html = post.get('content', {}).get('rendered', '')
                    date_iso = post.get('date_gmt', post.get('date', '')) + "Z"
                    
                    img = None
                    try:
                        featured = post.get('_embedded', {}).get('wp:featuredmedia', [])
                        if featured:
                            img = featured[0].get('source_url')
                    except: pass

                    links_data[url] = {
                        'url': url,
                        'title': title,
                        'body_html': body_html,
                        'date_str': date_iso,
                        'image_url': self._get_ddg_proxy_url(img) if img else None
                    }
        except Exception as e:
            print(f"  Error API WP: {e}")

        # 2. RSS Fallback
        try:
            rss_url = "https://www.gasteizhoy.com/feed/"
            res = self.scraper.get(rss_url, headers=self.headers, timeout=15)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'xml')
                for item in soup.find_all('item'):
                    url = item.link.text if item.link else ''
                    if url and url not in links_data:
                        if "/comercios/" in url.lower() or "el-boulevard" in url.lower():
                            continue
                            
                        title = item.title.text if item.title else ''
                        if any(x in title.lower() for x in ['el boulevard', 'publirreportaje', 'patrocinado']):
                            continue

                        date_el = item.pubDate or item.find('dc:date')
                        date_iso = self._parse_date(date_el.text).isoformat() if date_el else None
                        
                        content_el = item.find('content:encoded')
                        body_html = content_el.text if content_el else (item.description.text if item.description else '')
                        
                        links_data[url] = {
                            'url': url,
                            'title': title,
                            'body_html': body_html,
                            'date_str': date_iso
                        }
        except Exception as e:
            print(f"  Error RSS fallback: {e}")

        # 3. Respaldo Portada
        try:
            res = self.scraper.get("https://www.gasteizhoy.com/", headers=self.headers, timeout=15)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                combined_selectors = soup.find_all(['h2', 'h3']) + soup.select('a.nueve-bloque-noticia, a.heronews, a.box-shadow, a.blogpost, a.breakblock.breakingtext, a.linknews, a.sixnewsblock')
                for item in combined_selectors:
                    a_tag = item.find('a') or item.find_parent('a') if item.name in ['h2', 'h3'] else item
                    if a_tag:
                        val = a_tag.get('href', '')
                        if val:
                            href = re.sub(r'\s+', '', val)
                            if "/comercios/" in href.lower() or "el-boulevard" in href.lower():
                                continue
                            
                            parent = a_tag.find_parent()
                            block_text = (a_tag.get_text() + ' ' + (parent.get_text() if parent else '')).lower()
                            if any(keyword in block_text or keyword in href.lower() for keyword in ['patrocinado', 'concurso', 'publirreportaje', 'el boulevard']):
                                continue
                            
                            full_url = self._normalize_url(f"https://www.gasteizhoy.com{href}" if not href.startswith("http") else href)
                            if full_url not in links_data:
                                links_data[full_url] = {'url': full_url}
        except Exception as e:
            print(f"Error portada Gasteiz Hoy: {e}")

        limit_72h = datetime.now(timezone.utc) - timedelta(hours=72)
        links_to_process = []
        for url in links_data.keys():
            if url in self.history: continue
            
            info = links_data[url]
            if info.get('date_str'):
                try:
                    if self._parse_date(info['date_str']) < limit_72h:
                        continue
                except: pass
            links_to_process.append(url)

        print(f"  Procesando {len(links_to_process)} nuevas noticias de Gasteiz Hoy (recientes)")
        for url in links_to_process[:50]:
            data = self._extract_gasteiz_hoy_detail(links_data[url])
            if data:
                self.news_data.append(data)
                self.history.add(url)
            time.sleep(0.5)

    def _extract_gasteiz_hoy_detail(self, link_info):
        url = link_info['url']
        body = None; title = link_info.get('title'); date = link_info.get('date_str'); image_url = link_info.get('image_url')
        
        if link_info.get('body_html'):
            soup_content = BeautifulSoup(link_info['body_html'], 'html.parser')
            p_tags = soup_content.find_all('p')
            body = self._clean_article_body(p_tags)
            if not body:
                body = soup_content.get_text(separator="\n\n").strip()
            if not date: date = datetime.now(timezone.utc).isoformat()
        else:
            try:
                res = self.scraper.get(url, headers=self.headers, timeout=10)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, 'html.parser')
                    if not title:
                        h1 = soup.find('h1')
                        title = h1.get_text().strip() if h1 else soup.title.string.split('|')[0].strip()
                    
                    p_tags = soup.select('div.entry-content p, article p, div.contenido p, main p') or soup.find_all('p')
                    body = self._clean_article_body(p_tags)
                    if not date:
                        meta_date = soup.find('meta', property='article:published_time')
                        date = meta_date['content'] if meta_date else datetime.now(timezone.utc).isoformat()
                    if not image_url:
                        image_url = self._get_ddg_proxy_url(self._get_og_image(soup))
                else: raise Exception(f"Status {res.status_code}")
            except:
                return None 

        if not body or not title:
            return None

        # Filtro final por seguridad
        content_lower = (title + " " + body).lower()
        if any(x in content_lower for x in ['el boulevard', 'publirreportaje', 'patrocinado']):
            return None

        sentiment = self._analyze_sentiment(title + " " + body)
        return {
            'title': title,
            'url': url,
            'source': 'Gasteiz Hoy',
            'date': date,
            'sentiment': sentiment,
            'image': image_url
        }

    def _clean_article_body(self, p_tags):
        clean_p = []
        for p in p_tags:
            text = p.get_text().strip()
            if len(text) > 40 and not any(x in text.lower() for x in ['cookies', 'leer más', 'notificaciones', 'haz clic']):
                clean_p.append(text)
        return "\n\n".join(clean_p)

    def _analyze_sentiment(self, text):
        try:
            return TextBlob(text).sentiment.polarity
        except:
            return 0

    def _parse_date(self, date_str):
        if not date_str: return datetime.now(timezone.utc)
        try:
            # Intentar parsear ISO y asegurar que sea aware (UTC)
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except:
            return datetime.now(timezone.utc)

if __name__ == "__main__":
    scraper = MultiScraper()
    scraper.run()
