import requests
import cloudscraper
from bs4 import BeautifulSoup
import json
import re
import time
import os
import hashlib
import urllib.parse
from datetime import datetime
from email.utils import parsedate_to_datetime
from dotenv import load_dotenv

load_dotenv()
HF_API_KEY = os.getenv("HF_TOKEN")

from analyze_sentiment import analyze_sentiment, translate_to_euskara, translate_to_polish, rewrite_article

class MultiScraper:
    def __init__(self, history_file='scraper/history.json', data_output='data/news.json'):
        self.history_file = history_file
        self.data_output = data_output
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        self.scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
        self.history = self._load_history()
        self.news_data = []
        os.makedirs('data/images', exist_ok=True)

    def _load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        return set()
                    return set(json.loads(content))
            except (json.JSONDecodeError, Exception) as e:
                print(f"Warning: Could not load history from {self.history_file}: {e}")
                print("Starting with fresh history.")
                return set()
        return set()

    def _save_history(self):
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(list(self.history), f, indent=4)

    def _cleanup_old_images(self):
        """Borra imágenes de más de 15 días para ahorrar espacio."""
        image_dir = 'data/images'
        if not os.path.exists(image_dir):
            return
            
        now = time.time()
        max_age = 15 * 24 * 60 * 60 # 15 días en segundos
        
        deleted_count = 0
        for filename in os.listdir(image_dir):
            file_path = os.path.join(image_dir, filename)
            if os.path.isfile(file_path):
                file_age = now - os.path.getmtime(file_path)
                if file_age > max_age:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except Exception as e:
                        print(f"Error al borrar {filename}: {e}")
        
        if deleted_count > 0:
            print(f"Limpieza completada: {deleted_count} imágenes antiguas eliminadas.")

    def _save_news(self):
        os.makedirs(os.path.dirname(self.data_output), exist_ok=True)
        # Combinar y eliminar duplicados por URL de nuevo por si acaso
        existing_news = []
        if os.path.exists(self.data_output):
            try:
                with open(self.data_output, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content.strip():
                        existing_news = json.loads(content)
            except Exception as e:
                print(f"Error reading existing news file: {e}")
                if os.path.getsize(self.data_output) > 10:
                    print("Aborting save to prevent wiping the database. Please verify data/news.json.")
                    return
                
        # Combinamos las noticias existentes con las nuevas
        all_news = existing_news + self.news_data
        
        def parse_date(date_str):
            try:
                return datetime.fromisoformat(date_str).replace(tzinfo=None)
            except:
                return datetime.min

        # Ordenar todas por fecha descendente (más recientes primero)
        all_news.sort(key=lambda x: parse_date(x.get('date', '')), reverse=True)

        unique_news = []
        seen_images = set()
        seen_titles = set()
        seen_urls = set()

        for item in all_news:
            url = item.get('url', '')
            title = item.get('title', '')
            body = item.get('body', '')
            img_url = item.get('image', '')
            
            if not title or not url:
                continue
                
            # 1. Filtro 'EN DIRECTO'
            if any(x in title.upper() or x in body.upper() for x in ["EN DIRECTO", "ZUZENEAN"]):
                continue

            # 2. Misma URL exacta
            if url in seen_urls:
                continue
                
            # 3. Misma Imagen (la clave para detectar la misma noticia de distinta fuente/momento)
            if img_url and img_url in seen_images:
                continue

            # 4. Normalizar título y evitar titulares muy similares
            clean_title = title.split('|')[0].split(' - ')[0].strip().lower()
            if ": " in clean_title[:15]:
                clean_title = clean_title.split(": ", 1)[1]
                
            norm_title = "".join(filter(str.isalnum, clean_title))
            title_prefix = norm_title[:35] # Usamos 35 caracteres para comparar
            
            if title_prefix and title_prefix in seen_titles:
                continue

            # Pasó los filtros, es única
            unique_news.append(item)
            seen_urls.add(url)
            if img_url:
                seen_images.add(img_url)
            if title_prefix:
                seen_titles.add(title_prefix)

        # Filtrar noticias con menos de 2 días de antigüedad usando un máximo de 100
        now = datetime.now()
        latest_news = []
        for item in unique_news:
            item_date = parse_date(item.get('date', ''))
            if (now - item_date).days < 2:
                latest_news.append(item)
        
        latest_news = latest_news[:100]
        
        with open(self.data_output, 'w', encoding='utf-8') as f:
            json.dump(latest_news, f, indent=2, ensure_ascii=False)

    def _normalize_url(self, url):
        """Elimina parámetros de consulta para evitar duplicados por variaciones de trackers"""
        if '?' in url:
            return url.split('?')[0]
        return url

    def _get_og_image(self, soup):
        """Extrae la imagen original de los meta tags og:image."""
        meta = soup.find('meta', property='og:image')
        if meta and meta.get('content'):
            return meta['content'].strip()
        return None

    def _get_ddg_proxy_url(self, original_url):
        """Envuelve una URL en el proxy de imágenes de DuckDuckGo."""
        if not original_url:
            return None
        try:
            # El "método DuckDuckGo" para evitar tracking/bloqueos y problemas legales
            encoded_url = urllib.parse.quote(original_url)
            return f"https://external-content.duckduckgo.com/iu/?u={encoded_url}"
        except:
            return original_url

    def scrape_el_correo(self):
        url = "https://www.elcorreo.com/alava/araba/"
        print(f"Scrapeando El Correo: {url}")
        try:
            res = self.scraper.get(url, headers=self.headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            links = []
            for a in soup.select('a.v-a-link, a.v-prp__a, h2 a, h3 a'):
                href = a.get('href', '')
                if href.endswith(".html") and "vitoria" in href.lower() or "/araba/" in href:
                    full_url = self._normalize_url(f"https://www.elcorreo.com{href}" if not href.startswith("http") else href)
                    if full_url not in self.history:
                        links.append(full_url)
            
            for link in links[:30]: # Limitamos por fuente para no saturar
                data = self._extract_el_correo_detail(link)
                if data:
                    self.news_data.append(data)
                    self.history.add(link)
                time.sleep(1)
        except Exception as e:
            print(f"Error en El Correo: {e}")

    def _extract_el_correo_detail(self, url):
        try:
            res = self.scraper.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Metadata from JSON-LD
            title = ""
            date = ""
            script_tag = soup.find('script', type='application/ld+json')
            if script_tag:
                ld = json.loads(script_tag.string)
                if isinstance(ld, list): ld = ld[0]
                if "@graph" in ld:
                    articles = [item for item in ld["@graph"] if item.get("@type") in ["NewsArticle", "Article"]]
                    if articles: ld = articles[0]
                title = ld.get('headline', '')
                date = ld.get('datePublished', '')

            # Body from paragraphs
            p_tags = soup.select('div.v-p-b p, article p')
            body = self._clean_article_body(p_tags)
            if not body or "patrocinado" in title.lower() or "patrocinado" in body.lower(): 
                return None
            
            sentiment, score, category = analyze_sentiment(title + " " + body[:500])
            article_id = hashlib.md5(url.encode()).hexdigest()[:10]
            
            # Usar imagen original envuelta en proxy de DuckDuckGo
            image_url = self._get_ddg_proxy_url(self._get_og_image(soup))

            title_eu, body_eu = translate_to_euskara(title, body)
            time.sleep(1)
            title_pl, body_pl = translate_to_polish(title, body)
            time.sleep(1)
            title_rw, body_rw = rewrite_article(title, body)

            return {
                'id': article_id,
                'source': 'El Correo',
                'url': url,
                'title': title_rw or title or soup.title.string,
                'title_eu': title_eu,
                'title_pl': title_pl,
                'image': image_url,
                'body': body_rw or body,
                'body_eu': body_eu,
                'body_pl': body_pl,
                'date': date,
                'sentiment': sentiment,
                'score': score,
                'category': category,
                'lang': 'es'
            }
        except:
            return None

    def scrape_gasteiz_hoy(self):
        url = "https://www.gasteizhoy.com/"
        print(f"Scrapeando Gasteiz Hoy: {url}")
        try:
            res = self.scraper.get(url, headers=self.headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            links = []
            
            combined_selectors = soup.find_all(['h2', 'h3']) + soup.select('a.nueve-bloque-noticia, a.heronews, a.box-shadow, a.blogpost, a.breakblock.breakingtext, a.linknews, a.sixnewsblock')
            
            for item in combined_selectors:
                if item.name in ['h2', 'h3']:
                    a_tag = item.find('a') or item.find_parent('a')
                else:
                    a_tag = item
                
                if a_tag:
                    val = a_tag.get('href', '')
                    if val:
                        href = re.sub(r'\s+', '', val)
                        # Limpiar href de slash inicial redundante si es necesario
                        full_url = self._normalize_url(f"https://www.gasteizhoy.com{href}" if not href.startswith("http") else href)
                        if full_url not in self.history and full_url not in links:
                            links.append(full_url)
            
            for link in links[:30]:
                data = self._extract_gasteiz_hoy_detail(link)
                if data:
                    self.news_data.append(data)
                    self.history.add(link)
                time.sleep(1)
        except Exception as e:
            print(f"Error en Gasteiz Hoy: {e}")

    def _extract_gasteiz_hoy_detail(self, url):
        try:
            res = self.scraper.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            h1 = soup.find('h1')
            title = h1.get_text().strip() if h1 else soup.title.string.split('|')[0].strip()
            
            p_tags = soup.select('div.entry-content p, article p, div.contenido p, main p')
            if not p_tags:
                p_tags = soup.find_all('p')
            body = self._clean_article_body(p_tags)
            if not body or "patrocinado" in title.lower() or "patrocinado" in body.lower(): 
                return None
            
            # Intentar extraer fecha del span.published (nuevo formato) o de time tag
            date_tag = soup.find('span', class_='published')
            if date_tag and date_tag.get('title'):
                date = self._parse_spanish_date(date_tag['title'])
            else:
                date_tag_time = soup.find('time')
                date = date_tag_time['datetime'] if date_tag_time else datetime.now().isoformat()
            
            sentiment, score, category = analyze_sentiment(title + " " + body[:500])
            article_id = hashlib.md5(url.encode()).hexdigest()[:10]
            
            # Usar imagen original envuelta en proxy de DuckDuckGo
            image_url = self._get_ddg_proxy_url(self._get_og_image(soup))

            title_eu, body_eu = translate_to_euskara(title, body)
            time.sleep(1)
            title_pl, body_pl = translate_to_polish(title, body)
            time.sleep(1)
            title_rw, body_rw = rewrite_article(title, body)

            return {
                'id': article_id,
                'source': 'Gasteiz Hoy',
                'url': url,
                'title': title_rw or title,
                'title_eu': title_eu,
                'title_pl': title_pl,
                'image': image_url,
                'body': body_rw or body,
                'body_eu': body_eu,
                'body_pl': body_pl,
                'date': date,
                'sentiment': sentiment,
                'score': score,
                'category': category,
                'lang': 'es'
            }
        except:
            return None

    def _parse_spanish_date(self, date_str):
        """Parsea fechas tipo: sábado, 28 marzo, 2026, 7:58"""
        if not date_str:
            return datetime.now().isoformat()
        try:
            # Eliminar comas y pasar a minúsculas
            clean_str = date_str.lower().replace(',', '').strip()
            parts = clean_str.split()
            # Esperamos algo como: [día_semana, día, mes, año, hora] o [día, mes, año, hora]
            
            months = {
                'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
                'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
                'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
            }
            
            day = None
            month = None
            year = None
            time_val = "00:00"
            
            for part in parts:
                if part in months:
                    month = months[part]
                elif ':' in part:
                    time_val = part
                elif part.isdigit():
                    val = int(part)
                    if val > 2000:
                        year = val
                    else:
                        day = val
            
            if day and month and year:
                h, m = map(int, time_val.split(':'))
                return datetime(year, month, day, h, m).isoformat()
        except Exception as e:
            print(f"Error parsing date '{date_str}': {e}")
            
        return datetime.now().isoformat()



    def _clean_article_body(self, p_tags):
        blacklist = [
            "©", "todos los derechos reservados", 
            "una publicación compartida de", "síguenos en redes",
            "fotografía:", "cedida", "| actualizado",
            "lee la noticia completa", "suscríbete a",
            "el acceso al contenido premium",
            "por favor, inténtalo pasados unos minutos",
            "al iniciar sesión desde un dispositivo",
            "inicie sesión en este dispositivo",
            "primer periódico digital de vitoria",
            "noticias vitoria-álava"
        ]
        
        valid_paragraphs = []
        for p in p_tags:
            # Limpiar espacios y saltos de línea internos que rompen el regex
            text = " ".join(p.get_text().split()).strip()
            
            # 1. Limpieza específica de DNA (Fechas, autores y prefijos)
            # Eliminar patrones tipo: 25·03·26 | 18:30 (ahora sin saltos de línea internos)
            text = re.sub(r'^\d{2}·\d{2}·\d{2}\s*\|\s*\d{2}:\d{2}(\s*\|\s*Actualizado.*?)?', '', text).strip()
            text = re.sub(r'^\|\s*\d{2}:\d{2}', '', text).strip() # Caso de barra huérfana
            
            # Eliminar "En imágenes: ..." al principio
            text = re.sub(r'^en imágenes:.*$', '', text, flags=re.IGNORECASE).strip()
            
            # 2. Heurística para Nombres de Autores
            # Si el párrafo es muy corto (autor solo) o comienza con nombre de autor conocido
            if len(valid_paragraphs) <= 1 and len(text) < 40:
                # Si parece un nombre (Palabras con Mayúsculas)
                if text.istitle() or re.match(r'^[A-Z][a-z]+\s[A-Z][a-z]+', text):
                    continue

            # Skip short lines
            if len(text) < 40:
                continue
                
            # Skip if contains blacklist phrases
            text_lower = text.lower()
            if any(b in text_lower for b in blacklist):
                continue
                
            # Skip if it looks like a date/time header (e.g. 25·03·26 | 18:50 | Actualizado)
            if text.count('|') >= 2 and "actualizado" in text_lower:
                continue
                
            valid_paragraphs.append(text)
            
        return "\n".join(valid_paragraphs)



    def _calculate_daily_mood(self):
        try:
            mood_file = 'data/mood_history.json'
            mood_history = []
            if os.path.exists(mood_file):
                with open(mood_file, 'r', encoding='utf-8') as f:
                    mood_history = json.load(f)

            if not os.path.exists('data/news.json'):
                return
                
            with open('data/news.json', 'r', encoding='utf-8') as f:
                news = json.load(f)
            
            today_str = datetime.now().strftime("%Y-%m-%d")
            today_scores = []
            
            for item in news:
                item_date = item.get('date', '')
                if item_date.startswith(today_str):
                    today_scores.append(item.get('score', 0))
                    
            if not today_scores:
                return
                
            avg_score = round(sum(today_scores) / len(today_scores), 2)
            
            found = False
            for entry in mood_history:
                if entry.get('date') == today_str:
                    entry['score'] = avg_score
                    found = True
                    break
                    
            if not found:
                mood_history.append({"date": today_str, "score": avg_score})
                
            mood_history = sorted(mood_history, key=lambda x: x['date'])[-14:]
            
            with open(mood_file, 'w', encoding='utf-8') as f:
                json.dump(mood_history, f, indent=4, ensure_ascii=False)
                
            print(f"Daily mood calculated for {today_str}: {avg_score}")
        except Exception as e:
            print(f"Error calculating daily mood: {e}")

    def run(self):
        self.scrape_el_correo()
        self.scrape_gasteiz_hoy()
        self._save_news()
        self._save_history()
        self._cleanup_old_images()
        self._calculate_daily_mood()
        print(f"Total noticias nuevas procesadas: {len(self.news_data)}")

if __name__ == "__main__":
    scraper = MultiScraper()
    scraper.run()
