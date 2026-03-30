import cloudscraper
from bs4 import BeautifulSoup
import re

scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
res = scraper.get('https://www.gasteizhoy.com/', headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
soup = BeautifulSoup(res.text, 'html.parser')

combined_selectors = soup.find_all(['h2', 'h3']) + soup.select('a.nueve-bloque-noticia, a.heronews, a.box-shadow, a.blogpost, a.breakblock.breakingtext, a.linknews, a.sixnewsblock')

for item in combined_selectors:
    if item.name in ['h2', 'h3']:
        a_tag = item.find('a') or item.find_parent('a')
    else:
        a_tag = item
        
    if a_tag:
        val = a_tag.get('href', '')
        if val:
            href_clean = re.sub(r'\s+', '', val)
            if 'sibari-republic' in href_clean or 'concurso' in href_clean:
                print("--- FOUND:", href_clean)
                print("Text inside node:", item.get_text(strip=True))
                parent = item.find_parent()
                if parent:
                    print("Parent class:", parent.get('class', []))
                    print("Parent text:", parent.get_text(separator=' ', strip=True)[:100])
                    
