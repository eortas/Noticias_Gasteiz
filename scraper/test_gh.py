import cloudscraper
from bs4 import BeautifulSoup
import re

scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
res = scraper.get('https://www.gasteizhoy.com/', headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
soup = BeautifulSoup(res.text, 'html.parser')

combined_selectors = soup.find_all(['h2', 'h3']) + soup.select('a.nueve-bloque-noticia, a.heronews, a.box-shadow, a.blogpost, a.breakblock.breakingtext, a.linknews, a.sixnewsblock')
            
links = []
urls = []
for item in combined_selectors:
    if item.name in ['h2', 'h3']:
        a_tag = item.find('a') or item.find_parent('a')
    else:
        a_tag = item
    
    if a_tag:
        href = a_tag.get('href', '')
        if href:
            href_clean = re.sub(r'\s+', '', href)
            if href_clean not in urls:
                urls.append(href_clean)

with open('scraper/test_output.txt', 'w', encoding='utf-8') as f:
    f.write(f"Status Code: {res.status_code}\n")
    f.write(f"Total valid links found: {len(urls)}\n\n")
    for u in urls[:10]:
         f.write(u + "\n")
