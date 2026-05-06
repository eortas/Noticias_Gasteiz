import requests
import cloudscraper
from bs4 import BeautifulSoup
import json
import re
import time
import os
import hashlib
import urllib.parse
from datetime import datetime, timedelta, timezone
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
                    return
                
        all_news = existing_news + self.news_data
        
        def parse_date(date_str):
            if not date_str: 
                return datetime.min.replace(tzinfo=timezone.utc)
            try:
                # Normalizar formato Z a offset +00:00
                clean_date = date_str.replace('Z', '+00:00')
                dt = datetime.fromisoformat(clean_date)
                # Si es "naive" (sin zona horaria), asumimos UTC+2 (España verano)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone(timedelta(hours=2)))
                return dt
            except:
                return datetime.min.replace(tzinfo=timezone.utc)

        # Ordenar todas por fecha descendente
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
                
            if any(x in title.upper() or x in body.upper() for x in ["EN DIRECTO", "ZUZENEAN"]):
                continue
                
            if "viñeta de cerrajería" in title.lower():
                continue

            if url in seen_urls:
                continue
                
            if img_url and img_url in seen_images:
                continue

            clean_title = title.split('|')[0].split(' - ')[0].strip().lower()
            if ": " in clean_title[:15]:
                clean_title = clean_title.split(": ", 1)[1]
                
            norm_title = "".join(filter(str.isalnum, clean_title))
            title_prefix = norm_title[:35]
            
            if title_prefix and title_prefix in seen_titles:
                continue

            unique_news.append(item)
            seen_urls.add(url)
            if img_url: seen_images.add(img_url)
            if title_prefix: seen_titles.add(title_prefix)

        # Filtro "HOY Y AYER" (con margen de seguridad de 3 días para evitar problemas de TZ)
        now = datetime.now(timezone.utc)
        limit_date = (now - timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        latest_news = []
        for item in unique_news:
            item_dt = parse_date(item.get('date', ''))
            if item_dt >= limit_date:
                latest_news.append(item)
        
        # Cap de seguridad opcional
        latest_news = latest_news[:100]
        
        with open(self.data_output, 'w', encoding='utf-8') as f:
            json.dump(latest_news, f, indent=2, ensure_ascii=False)
        
        print(f"Scraping completado. Guardadas {len(latest_news)} noticias de hoy y ayer.")

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
        url = "https://www.elcorreo.com/alava/araba/"
        print(f"Scrapeando El Correo: {url}")
        try:
            res = self.scraper.get(url, headers=self.headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            links = []
            for a in soup.select('a.v-a-link, a.v-prp__a, h2 a, h3 a'):
                href = a.get('href', '')
                if href.endswith(".html") and "vitoria" in href.lower() or "/araba/" in href:
                    parent = a.find_parent()
                    block_text = (a.get_text() + ' ' + (parent.get_text() if parent else '')).lower()
                    if any(keyword in block_text or keyword in href.lower() for keyword in ['patrocinado', 'concurso', 'publirreportaje', 'publireportaje']):
                        continue
                        
                    full_url = self._normalize_url(f"https://www.elcorreo.com{href}" if not href.startswith("http") else href)
                    if full_url not in self.history:
                        links.append(full_url)
            
            for link in links[:30]:
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
            title = ""; date = ""
            script_tag = soup.find('script', type='application/ld+json')
            if script_tag:
                ld = json.loads(script_tag.string)
                if isinstance(ld, list): ld = ld[0]
                if "@graph" in ld:
                    articles = [item for item in ld["@graph"] if item.get("@type") in ["NewsArticle", "Article"]]
                    if articles: ld = articles[0]
                title = ld.get('headline', '')
                date = ld.get('datePublished', '')

            p_tags = soup.select('div.v-p-b p, article p')
            body = self._clean_article_body(p_tags)
            if not body or "patrocinado" in title.lower() or "patrocinado" in body.lower(): 
                return None
            
            sentiment, score, category = analyze_sentiment(title + " " + body[:500])
            article_id = hashlib.md5(url.encode()).hexdigest()[:10]
            image_url = self._get_ddg_proxy_url(self._get_og_image(soup))

            title_rw, body_rw = rewrite_article(title, body)
            time.sleep(1)
            title_eu, body_eu = translate_to_euskara(title_rw or title, body_rw or body)
            time.sleep(1)
            title_pl, body_pl = translate_to_polish(title_rw or title, body_rw or body)

            return {
                'id': article_id, 'source': 'El Correo', 'url': url,
                'title': title_rw or title or soup.title.string,
                'title_eu': title_eu, 'title_pl': title_pl,
                'image': image_url, 'body': body_rw or body,
                'body_eu': body_eu, 'body_pl': body_pl,
                'date': date, 'sentiment': sentiment, 'score': score,
                'category': category, 'lang': 'es'
            }
        except: return None

    def scrape_gasteiz_hoy(self):
        print(f"Scrapeando Gasteiz Hoy (RSS vía rss2json)")
        links_data = {}
        try:
            res_rss = requests.get("https://api.rss2json.com/v1/api.json?rss_url=https://www.gasteizhoy.com/feed/", timeout=15)
            if res_rss.status_code == 200:
                data = res_rss.json()
                if data.get('status') == 'ok':
                    for item in data.get('items', []):
                        url = self._normalize_url(item.get('link', '').strip())
                        if url:
                            body_html = item.get('content', '') or item.get('description', '')
                            links_data[url] = {
                                'url': url, 'title': item.get('title', ''),
                                'body_html': body_html, 'date_str': item.get('pubDate', '')
                            }
        except Exception as e:
            print(f"Error RSS Gasteiz Hoy: {e}")

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
                            parent = a_tag.find_parent()
                            block_text = (a_tag.get_text() + ' ' + (parent.get_text() if parent else '')).lower()
                            if any(keyword in block_text or keyword in href.lower() for keyword in ['patrocinado', 'concurso', 'publirreportaje']):
                                continue
                            full_url = self._normalize_url(f"https://www.gasteizhoy.com{href}" if not href.startswith("http") else href)
                            if full_url not in links_data:
                                links_data[full_url] = {'url': full_url}
        except Exception as e:
            print(f"Error portada Gasteiz Hoy: {e}")

        links_to_process = [url for url in links_data.keys() if url not in self.history]
        for url in links_to_process[:30]:
            data = self._extract_gasteiz_hoy_detail(links_data[url])
            if data:
                self.news_data.append(data)
                self.history.add(url)
            time.sleep(1)

    def _extract_gasteiz_hoy_detail(self, link_info):
        url = link_info['url']
        body = None; title = None; date = None; image_url = None
        try:
            res = self.scraper.get(url, headers=self.headers, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                h1 = soup.find('h1')
                title = h1.get_text().strip() if h1 else soup.title.string.split('|')[0].strip()
                p_tags = soup.select('div.entry-content p, article p, div.contenido p, main p') or soup.find_all('p')
                body = self._clean_article_body(p_tags)
                meta_date = soup.find('meta', property='article:published_time')
                date = meta_date['content'] if meta_date else datetime.now().isoformat()
                image_url = self._get_ddg_proxy_url(self._get_og_image(soup))
            else: raise Exception(f"Status {res.status_code}")
        except Exception as e:
            if not link_info.get('title'): return None
            title = link_info['title']
            soup_rss = BeautifulSoup(link_info['body_html'], 'html.parser')
            body = self._clean_article_body(soup_rss.find_all('p')) or soup_rss.get_text()[:2000]
            if link_info.get('date_str'):
                date = datetime.fromisoformat(link_info['date_str'].replace(' ', 'T')).isoformat()
            else: date = datetime.now().isoformat()
            img_tag = soup_rss.find('img')
            image_url = self._get_ddg_proxy_url(img_tag['src']) if img_tag and img_tag.get('src') else None

        if not body or "patrocinado" in title.lower() or "patrocinado" in body.lower(): return None
        
        try:
            sentiment, score, category = analyze_sentiment(title + " " + body[:500])
            article_id = hashlib.md5(url.encode()).hexdigest()[:10]
            title_rw, body_rw = rewrite_article(title, body)
            time.sleep(1)
            title_eu, body_eu = translate_to_euskara(title_rw or title, body_rw or body)
            time.sleep(1)
            title_pl, body_pl = translate_to_polish(title_rw or title, body_rw or body)
            return {
                'id': article_id, 'source': 'Gasteiz Hoy', 'url': url,
                'title': title_rw or title, 'title_eu': title_eu, 'title_pl': title_pl,
                'image': image_url, 'body': body_rw or body,
                'body_eu': body_eu, 'body_pl': body_pl,
                'date': date, 'sentiment': sentiment, 'score': score,
                'category': category, 'lang': 'es'
            }
        except: return None

    def _clean_article_body(self, p_tags):
        blacklist = ["©", "todos los derechos reservados", "nexus, la llave en mano", "la pescadería de mercadona", "hacienda vigila", "mercadona devolverá", "de 'got talent'", "un interno de dueñas", "dos pueblos de cádiz", "siete lugares donde antes se fumaba", "los jubilados que cobran", "pueden las aerolíneas", "guardia civil investiga", "casa de 'alto standing'", "mujer recibirá 125.000", "primer periódico digital de vitoria", "noticias vitoria-álava", "aparece primero en gasteiz hoy"]
        valid_paragraphs = []
        for p in p_tags:
            a_tag = p.find('a')
            if a_tag:
                href = a_tag.get('href', '')
                p_text_clean = p.get_text().strip()
                if (".html" in href or "gasteizhoy.com/" in href) and len(p_text_clean) < 180:
                    if len(a_tag.get_text().strip()) > len(p_text_clean) * 0.7: continue
            text = " ".join(p.get_text().split()).strip()
            text = re.sub(r'^\d{2}·\d{2}·\d{2}\s*\|\s*\d{2}:\d{2}(\s*\|\s*Actualizado.*?)?', '', text).strip()
            if len(text) < 40 or any(b in text.lower() for b in blacklist): continue
            valid_paragraphs.append(text)
        return "\n".join(valid_paragraphs)

    def _calculate_daily_mood(self):
        try:
            mood_file = 'data/mood_history.json'
            mood_history = []
            if os.path.exists(mood_file):
                with open(mood_file, 'r', encoding='utf-8') as f:
                    mood_history = json.load(f)
            if not os.path.exists('data/news.json'): return
            with open('data/news.json', 'r', encoding='utf-8') as f:
                news = json.load(f)
            today_str = datetime.now().strftime("%Y-%m-%d")
            today_scores = [item.get('score', 0) for item in news if item.get('date', '').startswith(today_str)]
            if not today_scores: return
            avg_score = round(sum(today_scores) / len(today_scores), 2)
            found = False
            for entry in mood_history:
                if entry.get('date') == today_str:
                    entry['score'] = avg_score; found = True; break
            if not found: mood_history.append({"date": today_str, "score": avg_score})
            mood_history = sorted(mood_history, key=lambda x: x['date'])[-14:]
            with open(mood_file, 'w', encoding='utf-8') as f:
                json.dump(mood_history, f, indent=4, ensure_ascii=False)
        except Exception as e: print(f"Error mood: {e}")

    def run(self):
        self.scrape_el_correo()
        self.scrape_gasteiz_hoy()
        self._save_news()
        self._save_history()
        self._cleanup_old_images()
        self._calculate_daily_mood()

if __name__ == "__main__":
    scraper = MultiScraper()
    scraper.run()
