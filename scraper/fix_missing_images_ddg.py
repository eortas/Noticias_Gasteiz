import json
import os
import re
import cloudscraper
import urllib.parse
import time
from bs4 import BeautifulSoup

scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

NEWS_FILE = 'data/news.json'

def get_ddg_proxy_url(original_url):
    if not original_url: return None
    try:
        encoded_url = urllib.parse.quote(original_url)
        return f"https://external-content.duckduckgo.com/iu/?u={encoded_url}"
    except:
        return original_url

def search_ddg_image(query):
    if not query: return None
    try:
        search_url = "https://duckduckgo.com/"
        res = scraper.get(search_url, params={"q": query}, timeout=10)
        vqd = re.search(r'vqd=([\d-]+)&', res.text)
        if not vqd:
            vqd = re.search(r'vqd=["\']([\d-]+)["\']', res.text)
        if vqd:
            vqd_token = vqd.group(1)
            img_api_url = "https://duckduckgo.com/i.js"
            params = {"q": query, "o": "json", "vqd": vqd_token, "f": ",,,", "p": "1"}
            res = scraper.get(img_api_url, params=params, timeout=10)
            time.sleep(1.0)
            data = res.json()
            if data.get("results"):
                for result in data["results"]:
                    if "gasteizhoy.com" in result.get("url", ""):
                        return get_ddg_proxy_url(result["image"])
                return get_ddg_proxy_url(data["results"][0]["image"])
    except: pass
    return None

def search_jina_image(url):
    try:
        jina_url = f"https://r.jina.ai/{url}"
        res = scraper.get(jina_url, timeout=20)
        if res.status_code == 200:
            match = re.search(r'!\[.*?\]\((https?://.*?)\)', res.text)
            if not match:
                match = re.search(r'(https?://[^\s)]+\.(?:jpg|jpeg|png|webp|gif))', res.text, re.IGNORECASE)
            if match:
                candidate = match.group(1)
                if not any(x in candidate.lower() for x in ["publicidad", "banner", "logo", "avatar", "icon", "pixel"]):
                    return get_ddg_proxy_url(candidate)
    except: pass
    return None

def search_jsonld_image(url):
    try:
        res = scraper.get(url, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string or script.get_text())
                    def find_img(d):
                        if isinstance(d, dict):
                            for k in ['image', 'thumbnailUrl']:
                                v = d.get(k)
                                if isinstance(v, str) and v.startswith('http'): return v
                                if isinstance(v, dict) and v.get('url'): return v.get('url')
                            for v in d.values():
                                res = find_img(v)
                                if res: return res
                        elif isinstance(d, list):
                            for i in d:
                                res = find_img(i)
                                if res: return res
                        return None
                    img = find_img(data)
                    if img: return get_ddg_proxy_url(img)
                except: continue
    except: pass
    return None

def fix_images():
    if not os.path.exists(NEWS_FILE): return
    with open(NEWS_FILE, 'r', encoding='utf-8') as f:
        news = json.load(f)
    updated = 0
    for item in news:
        if not item.get('image'):
            url = item.get('url')
            title = item.get('title')
            print(f"Reparando: {title[:30]}...")
            new_img = search_jsonld_image(url) or search_jina_image(url) or search_ddg_image(url) or search_ddg_image(f"{title} Gasteiz Hoy")
            if new_img:
                item['image'] = new_img
                updated += 1
    if updated > 0:
        with open(NEWS_FILE, 'w', encoding='utf-8') as f:
            json.dump(news, f, indent=2, ensure_ascii=False)
        print(f"Fixed {updated} images.")

if __name__ == '__main__':
    fix_images()
