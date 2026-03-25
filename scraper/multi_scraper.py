import requests
from bs4 import BeautifulSoup
import json
import time
import os
import hashlib
import urllib.parse
from datetime import datetime
from analyze_sentiment import analyze_sentiment

class MultiScraper:
    def __init__(self, history_file='scraper/history.json', data_output='data/news.json'):
        self.history_file = history_file
        self.data_output = data_output
        self.headers = {'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
        self.history = self._load_history()
        self.news_data = []

    def _load_history(self):
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        return set()

    def _save_history(self):
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(list(self.history), f)

    def _save_news(self):
        os.makedirs(os.path.dirname(self.data_output), exist_ok=True)
        # Cargamos noticias anteriores si existen para no perderlas (opcional, dependiendo de si queremos histórico total)
        existing_news = []
        if os.path.exists(self.data_output):
            try:
                with open(self.data_output, 'r', encoding='utf-8') as f:
                    existing_news = json.load(f)
            except:
                pass
        
        # Combinar y eliminar duplicados por URL de nuevo por si acaso
        all_news = self.news_data + existing_news
        unique_news = {item['url']: item for item in all_news}.values()
        
        # Ordenar por fecha descendente
        sorted_news = sorted(unique_news, key=lambda x: x.get('fecha', ''), reverse=True)
        
        with open(self.data_output, 'w', encoding='utf-8') as f:
            json.dump(list(sorted_news), f, indent=2, ensure_ascii=False)

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
            
            for link in links[:10]: # Limitamos por fuente para no saturar
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
            body = "\n".join([p.get_text().strip() for p in p_tags if len(p.get_text().strip()) > 40])
            
            sentiment, score = analyze_sentiment(title + " " + body[:500])
            article_id = hashlib.md5(url.encode()).hexdigest()[:10]
            
            # Generar imagen con Pollinations.ai
            prompt = urllib.parse.quote(f"News about {title} in Vitoria-Gasteiz, cinematic, professional photography, high resolution")
            image_url = f"https://pollinations.ai/p/{prompt}?width=1024&height=1024&nologo=true&seed={article_id}"

            return {
                'id': article_id,
                'source': 'El Correo',
                'url': url,
                'title': title or soup.title.string,
                'image': image_url,
                'body': body,
                'date': date,
                'sentiment': sentiment,
                'score': score
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
            for a in soup.select('h2.entry-title a, h3.entry-title a'):
                href = a.get('href', '')
                if href not in self.history:
                    links.append(href)
            
            for link in links[:10]:
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
            title = soup.find('h1', class_='entry-title').get_text().strip()
            body = "\n".join([p.get_text().strip() for p in soup.select('div.entry-content p') if len(p.get_text().strip()) > 30])
            date_tag = soup.find('time', class_='entry-date')
            date = date_tag['datetime'] if date_tag else datetime.now().isoformat()
            
            sentiment, score = analyze_sentiment(title + " " + body[:500])
            article_id = hashlib.md5(url.encode()).hexdigest()[:10]
            
            prompt = urllib.parse.quote(f"Vitoria-Gasteiz news: {title}, journalistic style, sharp focus, 4k")
            image_url = f"https://pollinations.ai/p/{prompt}?width=1024&height=1024&nologo=true&seed={article_id}"

            return {
                'id': article_id,
                'source': 'Gasteiz Hoy',
                'url': url,
                'title': title,
                'image': image_url,
                'body': body,
                'date': date,
                'sentiment': sentiment,
                'score': score
            }
        except:
            return None

    def scrape_dna(self):
        url = "https://www.noticiasdealava.eus/alava/vitoria/"
        print(f"Scrapeando DNA: {url}")
        try:
            res = requests.get(url, headers=self.headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            links = []
            for a in soup.select('h2.v-a__h a, a.v-a__h-l'):
                href = a.get('href', '')
                if href:
                    full_url = f"https://www.noticiasdealava.eus{href}" if not href.startswith("http") else href
                    if full_url not in self.history:
                        links.append(full_url)
            
            for link in links[:10]:
                data = self._extract_dna_detail(link)
                if data:
                    self.news_data.append(data)
                    self.history.add(link)
                time.sleep(1)
        except Exception as e:
            print(f"Error en DNA: {e}")

    def _extract_dna_detail(self, url):
        try:
            res = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            title = soup.find('h1').get_text().strip()
            body = "\n".join([p.get_text().strip() for p in soup.select('div.v-p-b p') if len(p.get_text().strip()) > 30])
            
            sentiment, score = analyze_sentiment(title + " " + body[:500])
            article_id = hashlib.md5(url.encode()).hexdigest()[:10]
            
            prompt = urllib.parse.quote(f"Vitoria news coverage: {title}, realistic, documentary style")
            image_url = f"https://pollinations.ai/p/{prompt}?width=1024&height=1024&nologo=true&seed={article_id}"

            return {
                'id': article_id,
                'source': 'Diario de Noticias',
                'url': url,
                'title': title,
                'image': image_url,
                'body': body,
                'date': datetime.now().isoformat(), # DNA uses complex dynamic dates often
                'sentiment': sentiment,
                'score': score
            }
        except:
            return None

    def run(self):
        self.scrape_el_correo()
        self.scrape_gasteiz_hoy()
        self.scrape_dna()
        self._save_news()
        self._save_history()
        print(f"Total noticias nuevas procesadas: {len(self.news_data)}")

if __name__ == "__main__":
    scraper = MultiScraper()
    scraper.run()
