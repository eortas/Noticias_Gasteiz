import os
import requests
import xml.etree.ElementTree as ET
import json
import re

def update_podcast_data():
    rss_url = "https://anchor.fm/s/1124a410c/podcast/rss"
    podcast_file = "data/podcast.json"
    
    try:
        response = requests.get(rss_url)
        response.raise_for_status()
        # Ensure we handle encoding correctly
        content = response.content.decode('utf-8')
        root = ET.fromstring(content)
        
        latest_es_slug = None
        latest_eu_slug = None
        latest_pl_slug = None
        
        for item in root.findall("./channel/item"):
            title = item.find("title").text or ""
            link_element = item.find("link")
            if link_element is None: continue
            link = link_element.text or ""
            
            # Extract the full slug after /episodes/
            slug_match = re.search(r'/episodes/([^/?]+)', link)
            if not slug_match: continue
            slug = slug_match.group(1)
            
            if title.startswith("(EU)"):
                if not latest_eu_slug:
                    latest_eu_slug = slug
            elif title.startswith("(PL)"):
                if not latest_pl_slug:
                    latest_pl_slug = slug
            else:
                if not latest_es_slug:
                    latest_es_slug = slug
            
            if latest_es_slug and latest_eu_slug and latest_pl_slug:
                break
        
        podcast_data = {
            "es_slug": latest_es_slug or "Noticias-del-da-06-de-Mayo-de-2026-e3ivd5k",
            "eu_slug": latest_eu_slug or "EU-2026ko-maiatzaren-6ko-albisteak-e3iven8",
            "pl_slug": latest_pl_slug or latest_es_slug, # Fallback to ES if PL not found
            "last_update": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        os.makedirs("data", exist_ok=True)
        with open(podcast_file, 'w', encoding='utf-8') as f:
            json.dump(podcast_data, f, indent=2)
            
        print(f"Podcast data updated: ES_SLUG={latest_es_slug}, EU_SLUG={latest_eu_slug}, PL_SLUG={latest_pl_slug}")
        
    except Exception as e:
        print(f"Error updating podcast data: {e}")

if __name__ == "__main__":
    import time
    update_podcast_data()
