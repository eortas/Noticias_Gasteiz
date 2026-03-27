import json
import os
import time
import sys

# Ensure scraper module can be imported
sys.path.append('c:\\Users\\ortas\\OneDrive\\Documentos\\Noticias_Gasteiz')
sys.path.append('c:\\Users\\ortas\\OneDrive\\Documentos\\Noticias_Gasteiz\\scraper')


from scraper.image_processor import process_and_save_image

NEWS_FILE = 'data/news.json'
MAPPING_FILE = 'data/original_images_map.json'

def backfill():
    if not os.path.exists(MAPPING_FILE):
        print("Mapping file not found.")
        return
        
    with open(NEWS_FILE, 'r', encoding='utf-8') as f:
        news = json.load(f)
        
    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
        
    updated = 0
    total = len(news)
    
    for i, item in enumerate(news[:500]):
        article_id = item.get('id')
        title = item.get('title')
        current_image = item.get('image')
        
        # Only process if not pollinations and have mapping
        if article_id in mapping:
            hotlink = mapping[article_id]
            print(f"[{i+1}/{total}] Backfilling {article_id} via img2img...")
            
            # process_and_save_image downloads the hotlink, transforms it, and saves it locally
            new_image = process_and_save_image(hotlink, article_id, title, output_dir='data/images')
            
            if new_image and new_image.startswith('data/images/'):
                item['image'] = new_image
                updated += 1
            
            # Small delay to respect HF API limits
            time.sleep(2)
            
            # Save progress periodically
            if updated > 0 and updated % 5 == 0:
                with open(NEWS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(news, f, indent=4, ensure_ascii=False)
                    
    # Final save
    with open(NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(news, f, indent=4, ensure_ascii=False)
        
    print(f"Finished backfill. Processed {updated} images using hotlinks.")

if __name__ == '__main__':
    backfill()
