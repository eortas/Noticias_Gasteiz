"""
Backfill script to find missing images for news articles.
Runs multiple strategies: direct scraper, Jina Reader, JSON-LD, data attrs, DDG search, Bing.
"""
import json
import os
import re
import cloudscraper
import urllib.parse
import time
import requests
from bs4 import BeautifulSoup

scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

NEWS_FILE = 'data/news.json'

USER_AGENTS = [
    ("chrome", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"),
    ("googlebot", "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"),
    ("safari", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"),
]

def get_ddg_proxy_url(original_url):
    if not original_url: return None
    try:
        if "duckduckgo.com/iu/?u=" in original_url:
            return original_url
        encoded_url = urllib.parse.quote(original_url)
        return f"https://external-content.duckduckgo.com/iu/?u={encoded_url}"
    except:
        return original_url

def get_og_image(soup):
    meta = soup.find('meta', attrs={'property': 'og:image'})
    if meta and meta.get('content'):
        return meta['content'].strip()
    meta = soup.find('meta', attrs={'name': 'twitter:image'})
    if meta and meta.get('content'):
        return meta['content'].strip()
    link = soup.find('link', rel='image_src')
    if link and link.get('href'):
        return link['href'].strip()
    return None

def find_image_in_jsonld(data):
    if isinstance(data, dict):
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
            found = find_image_in_jsonld(value)
            if found: return found
    elif isinstance(data, list):
        for item in data:
            found = find_image_in_jsonld(item)
            if found: return found
    return None

def extract_wordpress_image(soup):
    """Extract image using WP-specific selectors"""
    wp_selectors = [
        'figure.wp-block-image img',
        '.wp-block-post-featured-image img',
        'img.wp-post-image',
        '.entry-content img:first-of-type',
        '.post-thumbnail img',
        '.featured-image img',
        '.articulotexto img:first-of-type',
        '.contenido-noticia img:first-of-type',
        'article img:first-of-type',
        '.entry-content img',
        'main img',
        'img.size-full',
        'img.alignnone',
        'img.aligncenter',
        '.wp-block-image img',
    ]
    for selector in wp_selectors:
        img_tag = soup.select_one(selector)
        if img_tag and img_tag.get('src'):
            src = img_tag['src']
            if 'logo' not in src.lower() and 'icon' not in src.lower() and 'avatar' not in src.lower():
                return src

    # Last resort: any image with reasonable width
    for img in soup.find_all('img'):
        src = img.get('src') or img.get('data-src') or ''
        if any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
            if 'logo' not in src.lower() and 'icon' not in src.lower() and 'avatar' not in src.lower():
                width = img.get('width')
                try:
                    if width and int(width) >= 200:
                        return src
                except:
                    return src
    return None

def extract_data_attr_image(soup):
    """Extract image from data-* attributes like lazy loading"""
    for tag in soup.find_all(['img', 'figure']):
        for attr in ['data-src', 'data-original', 'data-lazy-src', 'data-large-image', 'data-featured-image']:
            val = tag.get(attr)
            if val and any(ext in val.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                if 'logo' not in val.lower():
                    return val
    return None

def fetch_direct_image(url):
    """Try to fetch the article directly and extract image with various methods"""
    for ua_name, ua_value in USER_AGENTS:
        try:
            headers = {
                'User-Agent': ua_value,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
            }
            fresh = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
            res = fresh.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                
                # Method 1: OG image
                img = get_og_image(soup)
                if img: return img, f"direct ({ua_name})"
                
                # Method 2: JSON-LD
                for script in soup.find_all('script', type='application/ld+json'):
                    try:
                        data = json.loads(script.string or script.get_text())
                        img = find_image_in_jsonld(data)
                        if img: return img, f"jsonld ({ua_name})"
                    except: continue
                
                # Method 3: WP selectors
                img = extract_wordpress_image(soup)
                if img: return img, f"wp_selectors ({ua_name})"
                
                # Method 4: Data attributes
                img = extract_data_attr_image(soup)
                if img: return img, f"data_attrs ({ua_name})"
        except:
            continue
    return None, None

def search_jina_image(url):
    try:
        jina_url = f"https://r.jina.ai/{url}"
        res = requests.get(jina_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        if res.status_code == 200:
            # Extract markdown content
            text = res.text
            marker = "Markdown Content:"
            if marker in text:
                text = text.split(marker, 1)[1].strip()
            # Look for markdown images
            match = re.search(r'!\[.*?\]\((https?://.*?)\)', text)
            if not match:
                match = re.search(r'(https?://[^\s)]+\.(?:jpg|jpeg|png|webp|gif))', text, re.IGNORECASE)
            if match:
                candidate = match.group(1)
                if not any(x in candidate.lower() for x in ["publicidad", "banner", "logo", "avatar", "icon", "pixel"]):
                    return candidate
    except: pass
    return None

def get_default_placeholder(source="", title=""):
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="450" viewBox="0 0 800 450">
  <defs>
    <linearGradient id="gasteizGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#3b82f6"/>
      <stop offset="25%" stop-color="#06b6d4"/>
      <stop offset="50%" stop-color="#10b981"/>
      <stop offset="75%" stop-color="#846358"/>
      <stop offset="100%" stop-color="#f43f5e"/>
    </linearGradient>
  </defs>
  <rect width="800" height="450" fill="#f8fafc"/>
  <rect x="20" y="20" width="760" height="410" fill="none" stroke="#cbd5e1" stroke-width="2" stroke-opacity="0.5" rx="12"/>
  <text x="50%" y="180" dominant-baseline="middle" text-anchor="middle" font-family="'Outfit', system-ui, -apple-system, sans-serif" font-weight="900" font-size="100" fill="url(#gasteizGrad)" letter-spacing="-2">Gasteiz</text>
  <text x="50%" y="290" dominant-baseline="middle" text-anchor="middle" font-family="'Outfit', system-ui, -apple-system, sans-serif" font-weight="900" font-size="100" fill="#0f172a" letter-spacing="-2">Live</text>
</svg>"""
    encoded_svg = urllib.parse.quote(svg.strip())
    return f"data:image/svg+xml;utf8,{encoded_svg}"

def search_ddg_image(query):
    """Devuelve el degradado vectorizado universal de Gasteiz Live en vez de buscar en la web."""
    print(f"  [Placeholder] Generada imagen por defecto en SVG de Gasteiz Live")
    return get_default_placeholder()

def fix_images():
    if not os.path.exists(NEWS_FILE): return
    with open(NEWS_FILE, 'r', encoding='utf-8') as f:
        news = json.load(f)
    updated = 0
    unchanged = 0
    
    for item in news:
        if item.get('image'):
            unchanged += 1
            continue
        
        url = item.get('url')
        title = item.get('title')
        print(f"\nReparando: {title[:50]}...")
        
        # Strategy 1: Direct scraper with multiple UAs
        new_img, method = fetch_direct_image(url)
        if new_img:
            print(f"  ✓ Imagen encontrada via {method}")
            item['image'] = get_ddg_proxy_url(new_img)
            updated += 1
            continue
        
        # Strategy 2: Jina Reader
        new_img = search_jina_image(url)
        if new_img:
            print(f"  ✓ Imagen encontrada via Jina Reader")
            item['image'] = get_ddg_proxy_url(new_img)
            updated += 1
            continue
        
        # Strategy 3: DDG search with URL
        new_img = search_ddg_image(url)
        if new_img:
            print(f"  ✓ Imagen encontrada via DDG (URL)")
            item['image'] = get_ddg_proxy_url(new_img)
            updated += 1
            continue
        
        # Strategy 4: DDG search with title + source
        if title:
            new_img = search_ddg_image(f"{title} Gasteiz Hoy")
            if new_img:
                print(f"  ✓ Imagen encontrada via DDG (title)")
                item['image'] = get_ddg_proxy_url(new_img)
                updated += 1
                continue
        
        # Strategy 5: DDG with keywords
        if title:
            keywords = title.split()[:8]
            new_img = search_ddg_image(' '.join(keywords) + ' Gasteiz Hoy')
            if new_img:
                print(f"  ✓ Imagen encontrada via DDG (keywords)")
                item['image'] = get_ddg_proxy_url(new_img)
                updated += 1
                continue
        
        print(f"  ✗ No se pudo encontrar imagen")
    
    if updated > 0:
        with open(NEWS_FILE, 'w', encoding='utf-8') as f:
            json.dump(news, f, indent=2, ensure_ascii=False)
        print(f"\n=== Fixed {updated} images. {unchanged} already had images. ===")
    else:
        print(f"\n=== No new images found. {unchanged} already had images. ===")

if __name__ == '__main__':
    fix_images()