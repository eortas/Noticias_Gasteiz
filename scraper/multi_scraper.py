import json
import os
import time
import re
import urllib.parse
import html as html_utils
import hashlib
from datetime import datetime, timedelta, timezone
import cloudscraper
import requests
from bs4 import BeautifulSoup

# Importar el analizador de sentimiento español basado en Groq/Llama
try:
    from scraper.analyze_sentiment import analyze_sentiment as groq_analyze_sentiment, heuristic_fallback
except ImportError:
    try:
        from analyze_sentiment import analyze_sentiment as groq_analyze_sentiment, heuristic_fallback
    except ImportError:
        groq_analyze_sentiment = None
        heuristic_fallback = None

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
        self.requests_session = requests.Session()
        self.requests_session.headers.update(self.headers)

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

        # Diario de Noticias de Álava
        try:
            self.scrape_diario_de_noticias()
        except Exception as e:
            print(f"Error Diario de Noticias: {e}")

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
        
        latest_news.sort(key=lambda item: self._parse_date(item.get('date', '')), reverse=True)

        # Cap de seguridad de max 200
        latest_news = latest_news[:200]
        
        with open(self.data_output, 'w', encoding='utf-8') as f:
            json.dump(latest_news, f, indent=2, ensure_ascii=False)
        
        print(f"Scraping completado. Guardadas {len(latest_news)} noticias de las últimas 72h.")

    def _get(self, url, timeout=15):
        last_error = None
        for client_name, getter in (
            ("cloudscraper", self.scraper.get),
            ("requests", self.requests_session.get),
        ):
            try:
                res = getter(url, headers=self.headers, timeout=timeout)
                if res.status_code == 200:
                    if client_name != "cloudscraper":
                        print(f"  OK via {client_name}: {url}")
                    return res
                print(f"  {client_name} status {res.status_code}: {url}")
            except Exception as e:
                last_error = e
                print(f"  {client_name} error {type(e).__name__}: {url} - {e}")
        if last_error:
            raise last_error
        return None

    def _jina_reader_url(self, url):
        if url.startswith("http://") or url.startswith("https://"):
            return f"https://r.jina.ai/{url}"
        return f"https://r.jina.ai/https://{url}"


    def _extract_jina_content(self, text):
        marker = "Markdown Content:"
        if marker in text:
            return text.split(marker, 1)[1].strip()
        return text

    def _get_via_jina(self, url, timeout=30):
        jina_url = self._jina_reader_url(url)
        try:
            res = self.scraper.get(jina_url, headers=self.headers, timeout=timeout)
            if res.status_code == 200:
                print(f"  OK via jina reader: {url}")
                return self._extract_jina_content(res.text)
            print(f"  jina reader status {res.status_code}: {url}")
        except Exception as e:
            print(f"  jina reader error {type(e).__name__}: {url} - {e}")
        return None

    def _get_json_with_reader_fallback(self, url, allow_reader=True):
        res = self._get(url, timeout=20)
        if res:
            return res.json()

        if not allow_reader:
            return None

        text = self._get_via_jina(url)
        if not text:
            return None

        try:
            return json.loads(text)
        except Exception as e:
            print(f"  Error parseando JSON desde jina reader: {e}")
            return None

    def _normalize_url(self, url):
        if '?' in url:
            return url.split('?')[0]
        return url

    def _search_ddg_image(self, query):
        """Busca una imagen real en DDG cuando el scraper falla. Técnica de respaldo avanzada."""
        if not query: return None
        print(f"  Buscando imagen de respaldo en DDG para: {query}")
        try:
            # 1. Obtener el token vqd
            search_url = "https://duckduckgo.com/"
            res = self.scraper.get(search_url, params={"q": query}, timeout=10)
            vqd = re.search(r'vqd=([\d-]+)&', res.text)
            if not vqd:
                vqd = re.search(r'vqd=["\']([\d-]+)["\']', res.text)
            
            if vqd:
                vqd_token = vqd.group(1)
                # 2. Llamar a la API interna de imágenes de DDG
                img_api_url = "https://duckduckgo.com/i.js"
                params = {
                    "q": query,
                    "o": "json",
                    "vqd": vqd_token,
                    "f": ",,,",
                    "p": "1"
                }
                res = self.scraper.get(img_api_url, params=params, timeout=10)
                time.sleep(1) # Pequeño delay para no saturar DDG
                data = res.json()
                if data.get("results"):
                    # Priorizar resultados de gasteizhoy.com si están disponibles
                    for result in data["results"]:
                        if "gasteizhoy.com" in result.get("url", ""):
                            return self._get_ddg_proxy_url(result["image"])
                    # Si no, el primer resultado
                    return self._get_ddg_proxy_url(data["results"][0]["image"])
        except Exception as e:
            print(f"  Error en búsqueda DDG ({query}): {e}")
        return None

    def _get_og_image(self, soup):
        # 1. Open Graph
        meta = soup.find('meta', attrs={'property': 'og:image'})
        if meta and meta.get('content'):
            return meta['content'].strip()
        # 2. Twitter
        meta = soup.find('meta', attrs={'name': 'twitter:image'})
        if meta and meta.get('content'):
            return meta['content'].strip()
        # 3. Schema.org / Thumbnail
        meta = soup.find('meta', attrs={'name': 'thumbnail'})
        if meta and meta.get('content'):
            return meta['content'].strip()
        # 4. Link image_src
        link = soup.find('link', rel='image_src')
        if link and link.get('href'):
            return link['href'].strip()
        return None

    def _get_ddg_proxy_url(self, original_url):
        if not original_url: return None
        if "duckduckgo.com/iu/?u=" in original_url:
            return original_url
        try:
            encoded_url = urllib.parse.quote(original_url)
            return f"https://external-content.duckduckgo.com/iu/?u={encoded_url}"
        except:
            return original_url

    def _is_excluded_title(self, title):
        title_lower = (title or "").lower()
        excluded = [
            'el boulevard',
            'publirreportaje',
            'patrocinado',
            'la viñeta de cerrajería',
            'la vineta de cerrajeria',
            'tira de cerrajería',
            'tira de cerrajeria',
            'el mirador',
            'vitoria hoy sabe de'
        ]
        return any(term in title_lower for term in excluded)

    def _clean_el_correo_paragraph(self, raw_text):
        text = html_utils.unescape(raw_text or "")
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _valid_el_correo_paragraph(self, text):
        if len(text) < 40:
            return False

        lower = text.lower()
        blacklist = [
            "©", "todos los derechos reservados", "vídeo es exclusivo",
            "disfruta de acceso", "inicia sesión", "temas", "comentarios",
            "suscríbete", "iniciar sesión", "lo más leído", "te puede interesar",
            "esta funcionalidad es exclusiva", "reporta un error", "whatsapp",
            "facebook"
        ]
        if any(item in lower for item in blacklist):
            return False

        if not re.search(r'[.!?…»"]$', text) and len(text.split()) < 20:
            return False

        return True

    def _find_article_body_in_jsonld(self, data):
        if isinstance(data, dict):
            body = data.get('articleBody')
            if isinstance(body, str) and body.strip():
                return body
            for value in data.values():
                found = self._find_article_body_in_jsonld(value)
                if found:
                    return found
        elif isinstance(data, list):
            for item in data:
                found = self._find_article_body_in_jsonld(item)
                if found:
                    return found
        return None

    def _extract_el_correo_body(self, html):
        soup = BeautifulSoup(html, 'html.parser')

        paragraphs = []
        seen = set()

        # El Correo publica los párrafos reales como p.v-d-p. Se extraen antes
        # que el JSON-LD porque articleBody llega como un único bloque corrido.
        selectors = [
            'article p.v-d-p',
            'main p.v-d-p',
            'p.v-d-p',
            'article p[class*="voc-p"]',
            'main p[class*="voc-p"]',
            'article p',
            'main p',
        ]
        for selector in selectors:
            for tag in soup.select(selector):
                text = self._clean_el_correo_paragraph(tag.get_text(" ", strip=True))
                if not self._valid_el_correo_paragraph(text):
                    continue
                key = text.lower()
                if key in seen:
                    continue
                seen.add(key)
                paragraphs.append(text)
            if len(paragraphs) >= 2:
                return "\n\n".join(paragraphs)

        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string or script.get_text())
            except Exception:
                continue

            body = self._find_article_body_in_jsonld(data)
            if not body:
                continue

            body = self._clean_el_correo_paragraph(body)
            body = re.sub(r'(?<=[a-záéíóúñ0-9][.!?])(?=[A-ZÁÉÍÓÚÑ¿¡])', ' ', body)
            if self._valid_el_correo_paragraph(body):
                return body

        return ""

    def _find_image_in_jsonld(self, data):
        if isinstance(data, dict):
            # Buscar en keys típicas de imagen
            for key in ['image', 'thumbnailUrl', 'primaryImageOfPage']:
                val = data.get(key)
                if isinstance(val, str) and val.startswith('http'):
                    return val
                if isinstance(val, dict) and val.get('url'):
                    return val.get('url')
                if isinstance(val, list) and val:
                    first = val[0]
                    if isinstance(first, str): return first
                    if isinstance(first, dict): return first.get('url')
            
            for value in data.values():
                found = self._find_image_in_jsonld(value)
                if found:
                    return found
        elif isinstance(data, list):
            for item in data:
                found = self._find_image_in_jsonld(item)
                if found:
                    return found
        return None


    def _scrape_el_correo_section(self, url, section_name, source_section, is_alava=False):
        import urllib.request
        print(f"Scrapeando El Correo ({section_name or 'Portada Alava'}): {url}")
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
                    if self._is_excluded_title(title):
                        continue
                    if is_alava and "/alava/" not in full_url and "/vitoria/" not in full_url:
                        continue

                    # Extraer cuerpo completo visitando el artículo con Googlebot
                    body_text = ""
                    try:
                        req = urllib.request.Request(full_url, headers=gb_headers)
                        with urllib.request.urlopen(req, timeout=10) as response:
                            html = response.read().decode('utf-8', errors='ignore')
                            body_text = self._extract_el_correo_body(html)
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

                    item = {
                        'id': article_id,
                        'title': title,
                        'url': full_url,
                        'source': 'El Correo',
                        'body': body_text,
                        'date': datetime.now(timezone.utc).isoformat(),
                        'sentiment': self._analyze_sentiment(title + " " + body_text),
                        'image': image,
                        'source_section': source_section
                    }
                    
                    if section_name:
                        item['category'] = section_name

                    self.news_data.append(item)
                    self.history.add(full_url)
                    time.sleep(1) # Pausa entre peticiones para evitar bloqueos
        except Exception as e:
            print(f"Error scraping El Correo ({section_name or 'Portada'}): {e}")

    def scrape_el_correo(self):
        self._scrape_el_correo_section("https://www.elcorreo.com/alava/araba/", None, "alava", is_alava=True)
        self._scrape_el_correo_section("https://www.elcorreo.com/economia/", "Economía", "economia")
        self._scrape_el_correo_section("https://www.elcorreo.com/sociedad/", "Sociedad", "sociedad")
        self._scrape_el_correo_section("https://www.elcorreo.com/alaves/", "Deportes", "deportes")
        self._scrape_el_correo_section("https://www.elcorreo.com/baskonia/", "Deportes", "deportes")
        self._scrape_el_correo_section("https://www.elcorreo.com/culturas/", "Cultura", "cultura")

    def scrape_gasteiz_hoy(self):
        print("Scrapeando Gasteiz Hoy (API WP + RSS + Portada)...")
        links_data = {}

        # 1. API WordPress
        api_urls = [
            "https://www.gasteizhoy.com/wp-json/wp/v2/posts?per_page=100&_embed",
            "https://www.gasteizhoy.com/wp-json/wp/v2/posts?per_page=100",
            "https://www.gasteizhoy.com/wp-json/wp/v2/posts?per_page=100&_fields=id,date,date_gmt,link,title",
        ]
        for api_url in api_urls:
            try:
                posts = self._get_json_with_reader_fallback(api_url, allow_reader="_fields=" in api_url)
                if not posts:
                    continue
                print(f"  API WP OK: {len(posts)} posts en {api_url}")
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
                    raw_date = post.get('date_gmt') or post.get('date') or datetime.now(timezone.utc).isoformat()
                    date_iso = raw_date if raw_date.endswith(('Z', '+00:00')) else raw_date + "Z"
                    
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
                if links_data:
                    break
            except Exception as e:
                print(f"  Error API WP: {e}")

        # 2. RSS Fallback
        try:
            rss_url = "https://www.gasteizhoy.com/feed/"
            res = self._get(rss_url, timeout=20)
            rss_text = res.text if res else self._get_via_jina(rss_url)
            if rss_text:
                soup = BeautifulSoup(rss_text, 'xml')
                rss_count = 0
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
                        rss_count += 1
                print(f"  RSS OK: {rss_count} enlaces añadidos")
        except Exception as e:
            print(f"  Error RSS fallback: {e}")

        # 3. Respaldo Portada
        try:
            home_url = "https://www.gasteizhoy.com/"
            res = self._get(home_url, timeout=20)
            home_text = res.text if res else self._get_via_jina(home_url)
            if home_text:
                soup = BeautifulSoup(home_text, 'html.parser')
                home_count = 0
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
                                home_count += 1
                print(f"  Portada OK: {home_count} enlaces añadidos")
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
            # Seleccionar p, li y encabezados para no perder listas ni estructura
            tags = soup_content.find_all(['p', 'li', 'h2', 'h3'])
            body = self._clean_article_body(tags)
            if not body:
                body = soup_content.get_text(separator="\n\n").strip()
            if not date: date = datetime.now(timezone.utc).isoformat()
            
            # If image is missing from API, try to find it in body_html
            if not image_url:
                first_img = soup_content.find('img')
                if first_img and first_img.get('src'):
                    image_url = self._get_ddg_proxy_url(first_img['src'])
        
        # If still missing image or body, fetch the page
        if not body or not image_url:
            try:
                res = self.scraper.get(url, headers=self.headers, timeout=10)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, 'html.parser')
                    if not title:
                        h1 = soup.find('h1')
                        title = h1.get_text().strip() if h1 else soup.title.string.split('|')[0].strip()
                    
                    if not body:
                        tags = soup.select('div.entry-content p, div.entry-content li, div.entry-content h2, div.entry-content h3, article p, article li, div.contenido p, main p, main li') or soup.find_all(['p', 'li', 'h2', 'h3'])
                        body = self._clean_article_body(tags)
                    
                    if not date:
                        meta_date = soup.find('meta', property='article:published_time')
                        date = meta_date['content'] if meta_date else datetime.now(timezone.utc).isoformat()
                    
                    if not image_url:
                        # Extract image from og:image or first content image
                        image_url = self._get_ddg_proxy_url(self._get_og_image(soup))
                        if not image_url:
                            img_tag = soup.select_one('article img, .entry-content img, main img')
                            if img_tag and img_tag.get('src'):
                                image_url = self._get_ddg_proxy_url(img_tag['src'])
                else: raise Exception(f"Status {res.status_code}")
            except Exception as e:
                # Print error if we are missing either body or image
                if not body or not image_url:
                    print(f"  Error detalle Gasteiz Hoy directo {url}: {e}")
                
                # FALLBACK 1: Fresh Scraper
                if not image_url:
                    try:
                        fresh_scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
                        res = fresh_scraper.get(url, headers=self.headers, timeout=10)
                        if res.status_code == 200:
                            soup = BeautifulSoup(res.text, 'html.parser')
                            image_url = self._get_ddg_proxy_url(self._get_og_image(soup))
                            
                            # Intento extra: JSON-LD
                            if not image_url:
                                for script in soup.find_all('script', type='application/ld+json'):
                                    try:
                                        data = json.loads(script.string or script.get_text())
                                        image_url = self._get_ddg_proxy_url(self._find_image_in_jsonld(data))
                                        if image_url: break
                                    except: continue
                            
                            if image_url: print(f"  Recuperada imagen via fresh scraper: {url}")
                    except: pass
                
                # FALLBACK 2: Jina Reader (Extracción de Markdown)
                if not image_url:
                    markdown = self._get_via_jina(url)
                    if markdown:
                        # Intento A: Regex de imagen Markdown estándar
                        match = re.search(r'!\[.*?\]\((https?://.*?)\)', markdown)
                        if not match:
                            # Intento B: Buscar cualquier URL de imagen en el texto si el primero falla
                            match = re.search(r'(https?://[^\s)]+\.(?:jpg|jpeg|png|webp|gif))', markdown, re.IGNORECASE)
                        
                        if match:
                            candidate = match.group(1)
                            # Filtro de ruido
                            if not any(x in candidate.lower() for x in ["publicidad", "banner", "logo", "avatar", "icon", "pixel"]):
                                image_url = self._get_ddg_proxy_url(candidate)
                                print(f"  Imagen recuperada via Jina Reader: {url}")

                # FALLBACK 3: DuckDuckGo Image Search (URL o Título)
                if not image_url:
                    # Intento A: Buscar por la URL exacta (Técnica sugerida por el usuario)
                    image_url = self._search_ddg_image(url)
                    if not image_url and title:
                        # Intento B: Buscar por titular + fuente
                        image_url = self._search_ddg_image(f"{title} Gasteiz Hoy")
                    
                    if image_url: 
                        print(f"  Imagen recuperada via DDG Search: {url}")

        if not body or not title:
            markdown = self._get_via_jina(url)
            if markdown:
                fallback = self._extract_gasteiz_hoy_markdown(link_info, markdown)
                if fallback:
                    return fallback
            return None

        # Filtro final por seguridad
        content_lower = (title + " " + body).lower()
        if any(x in content_lower for x in ['el boulevard', 'publirreportaje', 'patrocinado']):
            return None

        sentiment = self._analyze_sentiment(title + " " + body)
        return {
            'id': hashlib.md5(url.encode()).hexdigest()[:10],
            'title': title,
            'url': url,
            'source': 'Gasteiz Hoy',
            'body': body,
            'date': date,
            'sentiment': sentiment,
            'image': image_url
        }

    def _extract_gasteiz_hoy_markdown(self, link_info, markdown):
        url = link_info['url']
        title = link_info.get('title')
        image_url = link_info.get('image_url')
        paragraphs = []
        started = False

        for raw_line in markdown.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("# ") and not title:
                title = line[2:].strip()
                continue
            if title and title.lower() in line.lower():
                started = True
                continue
            if not started and line.startswith("**"):
                started = True

            if line.startswith("![") and not image_url:
                match = re.search(r'\((https?://[^)]+)\)', line)
                candidate = match.group(1) if match else None
                if candidate and not any(x in candidate.lower() for x in ["publicidad", "banner", "logo"]):
                    image_url = self._get_ddg_proxy_url(candidate)
                continue

            lower = line.lower()
            if (
                line.startswith(("#", "*", "[", "![", "[]("))
                or "http://" in lower
                or "https://" in lower
                or "publicidad" in lower
                or "close the sidebar" in lower
                or "buscar:" in lower
                or len(line) < 40
            ):
                continue

            clean_line = re.sub(r'[*_`]+', '', line).strip()
            if clean_line and clean_line not in paragraphs:
                paragraphs.append(clean_line)

        body_paragraphs = paragraphs[:12]
        
        # Regla estricta: cortar desde la aparición de "gasteiz hoy" si está en la segunda mitad
        cut_index = len(body_paragraphs)
        for i, p in enumerate(body_paragraphs):
            if i >= len(body_paragraphs) * 0.5 and "gasteiz hoy" in p.lower():
                cut_index = i
                break
                
        body = "\n\n".join(body_paragraphs[:cut_index])
        if not body or not title:
            return None

        content_lower = (title + " " + body).lower()
        if any(x in content_lower for x in ['el boulevard', 'publirreportaje', 'patrocinado']):
            return None

        return {
            'id': hashlib.md5(url.encode()).hexdigest()[:10],
            'title': title,
            'url': url,
            'source': 'Gasteiz Hoy',
            'body': body,
            'date': link_info.get('date_str') or datetime.now(timezone.utc).isoformat(),
            'sentiment': self._analyze_sentiment(title + " " + body),
            'image': image_url
        }

    def scrape_diario_de_noticias(self):
        print("Scrapeando Diario de Noticias de Álava y Vitoria-Gasteiz...")
        try:
            urls = [
                "https://www.noticiasdealava.eus/alava/",
                "https://www.noticiasdealava.eus/vitoria-gasteiz/"
            ]
            
            links = []
            for url in urls:
                try:
                    res = self._get(url, timeout=15)
                    if not res or res.status_code != 200:
                        print(f"  Error obteniendo la portada ({url}): {res.status_code if res else 'No response'}")
                        continue

                    soup = BeautifulSoup(res.content, 'html.parser')
                    
                    # Extraer enlaces
                    for a in soup.find_all('a', href=True):
                        href = a['href']
                        # Filtrar enlaces de Álava, Vitoria-Gasteiz o Gasteiz que terminen en .html
                        if any(x in href for x in ['/alava/', '/vitoria-gasteiz/', '/gasteiz/']):
                            if href.endswith('.html'):
                                full_url = href
                                if not full_url.startswith('http'):
                                    full_url = "https://www.noticiasdealava.eus" + full_url
                                
                                full_url = self._normalize_url(full_url)
                                if full_url not in links:
                                    links.append(full_url)
                except Exception as e:
                    print(f"  Error al procesar la portada {url}: {e}")

            print(f"  Encontrados {len(links)} enlaces potenciales en Diario de Noticias")
            
            # Procesar cada artículo nuevo
            count = 0
            for full_url in links[:30]: # Limitar a los primeros 30 para evitar sobrecarga
                if full_url in self.history:
                    continue
                
                print(f"  Procesando artículo de Diario de Noticias: {full_url}")
                try:
                    art_res = self._get(full_url, timeout=15)
                    if not art_res or art_res.status_code != 200:
                        continue
                    
                    art_soup = BeautifulSoup(art_res.content, 'html.parser')
                    
                    # 1. Título
                    h1 = art_soup.find('h1')
                    title = h1.get_text().strip() if h1 else ""
                    if not title:
                        continue
                    
                    if self._is_excluded_title(title):
                        continue
                    
                    # 2. Subtítulo
                    subtitle_el = art_soup.select_one('.article-subtitle, .subtitle, .lead, .entradilla, .article-lead')
                    subtitle = subtitle_el.get_text().strip() if subtitle_el else ""
                    
                    # 3. Párrafos
                    p_tags = art_soup.select('div.article-body p')
                    if not p_tags:
                        p_tags = art_soup.select('div.v-p-b p, article p, div.contenido p, main p')
                        
                    body_paragraphs = []
                    blacklist = [
                        "©", "todos los derechos reservados", "fotografía:", "cedida",
                        "síguenos en redes sociales", "siguenos en redes sociales", "2026"
                    ]
                    for p in p_tags:
                        text = " ".join(p.get_text().split()).strip()
                        if not text:
                            continue
                        if any(b in text.lower() for b in blacklist):
                            continue
                        if len(text) < 40:
                            continue
                        body_paragraphs.append(text)
                        
                    body_text = "\n\n".join(body_paragraphs)
                    if not body_text:
                        body_text = subtitle if subtitle else title
                        
                    # 4. Filtrar Patrocinados (Requisito estricto del usuario)
                    combined_text = (title + " " + subtitle + " " + body_text).lower()
                    if "contenido ofrecido por" in combined_text or "ofrecido por" in combined_text:
                        print(f"  [FILTRADO] Omitiendo noticia patrocinada por 'ofrecido por': {full_url}")
                        continue
                    
                    # 5. Imagen
                    image_url = self._get_og_image(art_soup)
                    if not image_url:
                        img_tag = art_soup.select_one('div.article-body img, article img')
                        if img_tag and img_tag.get('src'):
                            image_url = img_tag['src']
                            
                    if image_url:
                        image_url = self._get_ddg_proxy_url(image_url)
                    else:
                        image_url = self._search_ddg_image(f"{title} Diario de Noticias de Álava")
                        
                    # 6. Fecha
                    date = None
                    meta_date = art_soup.find('meta', property='article:published_time')
                    if meta_date and meta_date.get('content'):
                        date = meta_date['content']
                    
                    if not date:
                        for script in art_soup.find_all('script', type='application/ld+json'):
                            try:
                                data = json.loads(script.string or script.get_text())
                                if isinstance(data, dict) and data.get('datePublished'):
                                    date = data.get('datePublished')
                                    break
                                elif isinstance(data, list):
                                    for item in data:
                                        if isinstance(item, dict) and item.get('datePublished'):
                                            date = item.get('datePublished')
                                            break
                                    if date:
                                        break
                            except:
                                pass
                                
                    if not date:
                        date = datetime.now(timezone.utc).isoformat()
                        
                    # 7. Sentimiento
                    sentiment = self._analyze_sentiment(title + " " + body_text)
                    
                    article_id = hashlib.md5(full_url.encode()).hexdigest()[:10]
                    
                    item = {
                        'id': article_id,
                        'title': title,
                        'url': full_url,
                        'source': 'Diario de Noticias',
                        'body': body_text,
                        'date': date,
                        'sentiment': sentiment,
                        'image': image_url,
                        'source_section': 'alava'
                    }
                    
                    self.news_data.append(item)
                    self.history.add(full_url)
                    count += 1
                    time.sleep(1)
                    
                except Exception as ex:
                    print(f"  Error procesando detalle del artículo {full_url}: {ex}")
                    
            print(f"  Diario de Noticias completado. Añadidas {count} noticias nuevas.")
            
        except Exception as e:
            print(f"Error scraping Diario de Noticias: {e}")

    def _clean_article_body(self, tags):
        clean_p = []
        # Frases de autobombo detectadas en Gasteiz Hoy y otros
        blacklist = [
            'cookies', 'leer más', 'notificaciones', 'haz clic', 
            'en gasteiz hoy, seguimos informando', 'visión completa de la ciudad',
            'ofreciendo a nuestros lectores', 'nuestros lectores una visión',
            'noticias sobre ocio, turismo, obras', 'síguenos en redes sociales',
            'en el corazón de la ciudad, gasteiz hoy', 'se erige como el primer periódico digital',
            'ofreciendo una visión integral de la actualidad local', 'fuente confiable para los ciudadanos de vitoria-gasteiz',
            'enfoque de periodismo ciudadano e independiente', 'lectores alaveses que buscan una cobertura informativa rigurosa',
            'todos los derechos reservados'
        ]
        
        for tag in tags:
            text = tag.get_text().strip()
            # Bajamos el umbral a 25 para capturar puntos de listas cortos pero informativos
            if len(text) > 25:
                lower_text = text.lower()
                # Regla general: Si empieza por "En Gasteiz Hoy", es autobombo
                if lower_text.startswith("en gasteiz hoy"):
                    continue
                # Si empieza por "En el corazón de la ciudad", suele ser el nuevo autobombo
                if lower_text.startswith("en el corazón de la ciudad"):
                    continue
                    
                if not any(x in lower_text for x in blacklist):
                    # Si es un li, le añadimos un punto o guión para mantener formato de lista
                    if tag.name == 'li' and not text.startswith(('•', '-', '*')):
                        text = f"• {text}"
                    clean_p.append(text)
        
        # Regla estricta del usuario: si aparece "Gasteiz Hoy" en la segunda mitad del artículo, borrar desde ahí hasta el final.
        cut_index = len(clean_p)
        for i, p in enumerate(clean_p):
            if i >= len(clean_p) * 0.5 and "gasteiz hoy" in p.lower():
                cut_index = i
                break
                
        if cut_index < len(clean_p):
            clean_p = clean_p[:cut_index]

        return "\n\n".join(clean_p)

    # Contador de llamadas para rotar entre las dos keys de sentimiento
    _sentiment_call_count = 0

    def _analyze_sentiment(self, text):
        """Analiza sentimiento rotando entre todas las llaves de Groq disponibles.
        Fallback a heurística española si Groq no está disponible."""
        sentiment_keys = [
            os.environ.get("GROQ_REWRITE_2"), os.environ.get("GROQ_REWRITE_3"),
            os.environ.get("GROQ_REWRITE_KEY"), os.environ.get("groq_KEY"), 
            os.environ.get("GROQ_TRANSLATION_KEY"), os.environ.get("GROQ_POLISH_KEY"),
            os.environ.get("GROQ_EUSKERA2"), os.environ.get("GROQ_POLISH2"),
            os.environ.get("GROQ_API_KEY")
        ]
        valid_keys = [k for k in sentiment_keys if k]

        if groq_analyze_sentiment and valid_keys:
            # Rotar por número de llamada para distribuir carga
            api_key = valid_keys[MultiScraper._sentiment_call_count % len(valid_keys)]
            MultiScraper._sentiment_call_count += 1
            try:
                import os as _os
                _orig = _os.environ.get("GROQ_API_KEY")
                _os.environ["GROQ_API_KEY"] = api_key
                _sentiment_label, score, _category = groq_analyze_sentiment(text[:1000])
                if _orig is not None:
                    _os.environ["GROQ_API_KEY"] = _orig
                else:
                    _os.environ.pop("GROQ_API_KEY", None)
                return round(score, 4)
            except Exception as e:
                print(f"  Groq sentiment falló ({api_key[:8]}...): {e}, usando heurística")

        # Fallback heurístico español
        if heuristic_fallback:
            try:
                _label, score, _cat = heuristic_fallback(text)
                return round(score, 4)
            except:
                pass
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
