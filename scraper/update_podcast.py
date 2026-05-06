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
        root = ET.fromstring(response.content)
        
        latest_es = None
        latest_eu = None
        
        for item in root.findall("./channel/item"):
            title = item.find("title").text or ""
            link = item.find("link").text or ""
            
            # Extract episode ID from Anchor/Spotify link
            # Example: .../episodes/Noticias-...-e3ivd5k
            # The ID is usually the part after the last '-'
            match = re.search(r'-([a-zA-Z0-9]+)$', link.strip())
            episode_id = match.group(1) if match else None
            
            if not episode_id:
                # Fallback: try to extract from the end of the URL if no dash
                episode_id = link.strip().split('/')[-1]
            
            if title.startswith("(EU)"):
                if not latest_eu:
                    latest_eu = episode_id
            else:
                if not latest_es:
                    latest_es = episode_id
            
            if latest_es and latest_eu:
                break
        
        podcast_data = {
            "es": latest_es or "e3ivd5k", # Fallback to known good if none found
            "eu": latest_eu or "e3iven8",
            "last_update": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        os.makedirs("data", exist_ok=True)
        with open(podcast_file, 'w', encoding='utf-8') as f:
            json.dump(podcast_data, f, indent=2)
            
        print(f"Podcast data updated: ES={latest_es}, EU={latest_eu}")
        
    except Exception as e:
        print(f"Error updating podcast data: {e}")

if __name__ == "__main__":
    import time
    update_podcast_data()
