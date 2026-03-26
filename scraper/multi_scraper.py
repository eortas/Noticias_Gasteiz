import requests
from bs4 import BeautifulSoup
import json
import re
import time
import os
import hashlib
import urllib.parse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
HF_API_KEY = os.getenv("HF_TOKEN")

from analyze_sentiment import analyze_sentiment, translate_to_euskara, translate_to_polish, rewrite_article

class MultiScraper:
    def __init__(self, history_file='scraper/history.json', data_output='data/news.json'):
        self.history_file = history_file
        self.data_output = data_output
        self.headers = {'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
        self.history = self._load_history()
        self.news_data = []
        os.makedirs('data/images', exist_ok=True)

    def _load_history(self):
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return set(json.load(f))
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
        
        # Dedup logic: usaremos el título normalizado para evitar duplicados reales
        unique_news = {}
        for item in all_news:
            title = item.get('title', '')
            body = item.get('body', '')
            
            # 1. Filtro 'EN DIRECTO'
            if "EN DIRECTO" in title.upper() or "EN DIRECTO" in body.upper():
                continue
                
            # 2. Normalizar título: quitar fuentes comunes al final y limpiar espacios/puntuación
            clean_title = title.split('|')[0].split(' - ')[0].strip().lower()
            # Eliminar caracteres no alfanuméricos para la clave de deduplicación
            norm_title = "".join(filter(str.isalnum, clean_title))
            
            if not norm_title:
                norm_title = item['url']
                
            unique_news[norm_title] = item
        
        # Sort by date
        sorted_news = sorted(unique_news.values(), key=lambda x: x['date'], reverse=True)
        # Filtrar noticias con menos de 2 días de antigüedad
        now = datetime.now()
        latest_news = []
        for item in sorted_news:
            try:
                # Asegurar que el objeto item_date sea naive (sin zona horaria) para evitar errores de comparación
                item_date = datetime.fromisoformat(item['date']).replace(tzinfo=None)
                if (now - item_date).days < 2:
                    latest_news.append(item)
            except (ValueError, KeyError):
                # Si no hay fecha o está mal, la mantenemos si es nueva, o la descartamos si es vieja
                latest_news.append(item)
        
        # Opcional: Cap de seguridad de todas formas (ej. max 100)
        latest_news = latest_news[:100]
        
        with open(self.data_output, 'w', encoding='utf-8') as f:
            json.dump(latest_news, f, indent=2, ensure_ascii=False)

    def _generate_hf_image(self, title, article_id):
        if not HF_API_KEY:
            # Fallback a pollinations si no hay key
            prompt = urllib.parse.quote(f"Vitoria news: {title}, realistic photography")
            return f"https://pollinations.ai/p/{prompt}?width=1024&height=1024&nologo=true&seed={article_id}"
            
        file_path = f"data/images/{article_id}.jpg"
        if os.path.exists(file_path):
            return file_path
            
        models = [
            "black-forest-labs/FLUX.1-schnell",
            "stabilityai/stable-diffusion-xl-base-1.0",
            "runwayml/stable-diffusion-v1-5"
        ]
        
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        payload = {"inputs": f"Editorial news photography from Vitoria-Gasteiz: {title}. Realistic, high quality, documentary style."}
        
        for model in models:
            try:
                # Actualizamos a la nueva URL del router de Hugging Face
                API_URL = f"https://router.huggingface.co/hf-inference/models/{model}"
                response = requests.post(API_URL, headers=headers, json=payload, timeout=25)
                if response.status_code == 200:
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    time.sleep(2)
                    return file_path
                elif response.status_code == 503:
                    # El modelo se está cargando, esperamos un poco y saltamos al siguiente o reintentamos
                    continue
            except Exception:
                pass
                
        # Si todo falla en HF, volvemos a Pollinations como último recurso
        prompt = urllib.parse.quote(f"Vitoria news: {title}, realistic photography, cinematic")
        return f"https://pollinations.ai/p/{prompt}?width=1024&height=1024&nologo=true&seed={article_id}"

    def _get_og_image(self, soup):
        """Extrae la imagen original de los meta tags og:image."""
        meta = soup.find('meta', property='og:image')
        if meta and meta.get('content'):
            return meta['content'].strip()
        return None

    def scrape_el_correo(self):
        url = "https://www.elcorreo.com/alava/araba/"
        print(f"Scrapeando El Correo: {url}")
        try:
            res = requests.get(url, headers=self.headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            links = []
            for a in soup.select('a.v-a-link, a.v-prp__a, h2 a, h3 a'):
                href = a.get('href', '')
                if href.endswith(".html") and "vitoria" in href.lower() or "/araba/" in href:
                    full_url = f"https://www.elcorreo.com{href}" if not href.startswith("http") else href
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
            res = requests.get(url, headers=self.headers, timeout=10)
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
            
            # Intentar extraer imagen original, si no, generar con HF
            image_url = self._get_og_image(soup)
            if not image_url:
                image_url = self._generate_hf_image(title, article_id)

            title_eu, body_eu = translate_to_euskara(title, body)
            title_pl, body_pl = translate_to_polish(title, body)
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
            res = requests.get(url, headers=self.headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            links = []
            
            for tag in soup.find_all(['h2', 'h3']):
                a_tag = tag.find('a')
                if not a_tag:
                    a_tag = tag.find_parent('a')
                if a_tag:
                    href = a_tag.get('href', '')
                    if href:
                        full_url = f"https://www.gasteizhoy.com{href}" if not href.startswith("http") else href
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
            res = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            h1 = soup.find('h1')
            title = h1.get_text().strip() if h1 else soup.title.string.split('|')[0].strip()
            
            p_tags = soup.select('div.entry-content p, article p, div.contenido p, main p')
            if not p_tags:
                p_tags = soup.find_all('p')
            body = self._clean_article_body(p_tags)
            if not body or "patrocinado" in title.lower() or "patrocinado" in body.lower(): 
                return None
            
            date_tag = soup.find('time')
            date = date_tag['datetime'] if date_tag else datetime.now().isoformat()
            
            sentiment, score, category = analyze_sentiment(title + " " + body[:500])
            article_id = hashlib.md5(url.encode()).hexdigest()[:10]
            
            # Intentar extraer imagen original, si no, generar con HF
            image_url = self._get_og_image(soup)
            if not image_url:
                image_url = self._generate_hf_image(title, article_id)

            title_eu, body_eu = translate_to_euskara(title, body)
            title_pl, body_pl = translate_to_polish(title, body)
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

    def scrape_dna(self):
        url = "https://www.noticiasdealava.eus/vitoria-gasteiz/"
        print(f"Scrapeando DNA: {url}")
        try:
            res = requests.get(url, headers=self.headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            links = []
            for tag in soup.find_all(['h2', 'h3']):
                a_tag = tag.find('a')
                if not a_tag:
                    a_tag = tag.find_parent('a')
                if a_tag:
                    href = a_tag.get('href', '')
                    if href:
                        full_url = f"https://www.noticiasdealava.eus{href}" if not href.startswith("http") else href
                        if "vitoria" in full_url.lower() and full_url not in self.history and full_url not in links:
                            links.append(full_url)
            
            for link in links[:30]:
                data = self._extract_dna_detail(link)
                if data:
                    self.news_data.append(data)
                    self.history.add(link)
                time.sleep(1)
        except Exception as e:
            print(f"Error en DNA: {e}")

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

    def _extract_dna_detail(self, url):
        try:
            res = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            h1 = soup.find('h1')
            title = h1.get_text().strip() if h1 else soup.title.string.split('|')[0].strip()
            
            p_tags = soup.select('div.v-p-b p, article p, div.contenido p, main p')
            if not p_tags:
                p_tags = soup.find_all('p')
                
            body = self._clean_article_body(p_tags)
            if not body or "patrocinado" in title.lower() or "patrocinado" in body.lower(): 
                return None
            
            sentiment, score, category = analyze_sentiment(title + " " + body[:500])
            article_id = hashlib.md5(url.encode()).hexdigest()[:10]
            
            # Intentar extraer imagen original, si no, generar con HF
            image_url = self._get_og_image(soup)
            if not image_url:
                image_url = self._generate_hf_image(title, article_id)

            # DNA publishes bilingual content - detect if article is in Euskara
            is_eu = '/eu/' in url or url.endswith('-eu') or url.endswith('/eu')

            title_eu, body_eu = (title, body) if is_eu else translate_to_euskara(title, body)
            title_pl, body_pl = translate_to_polish(title, body)
            title_rw, body_rw = (None, None) if is_eu else rewrite_article(title, body)

            return {
                'id': article_id,
                'source': 'Diario de Noticias',
                'url': url,
                'title': title_rw or title,
                'title_eu': title_eu,
                'title_pl': title_pl,
                'image': image_url,
                'body': body_rw or body,
                'body_eu': body_eu,
                'body_pl': body_pl,
                'date': datetime.now().isoformat(),
                'sentiment': sentiment,
                'score': score,
                'category': category,
                'lang': 'eu' if is_eu else 'es'
            }
        except:
            return None

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
        self.scrape_dna()
        self._save_news()
        self._save_history()
        self._cleanup_old_images()
        self._calculate_daily_mood()
        print(f"Total noticias nuevas procesadas: {len(self.news_data)}")

if __name__ == "__main__":
    scraper = MultiScraper()
    scraper.run()
