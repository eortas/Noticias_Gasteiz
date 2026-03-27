import os
import sys
import json
import requests

# Add current directory to path for local imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from image_processor import process_and_save_image

# Path to the news database
NEWS_FILE = 'data/news.json'

def reprocess_all_images():
    """
    Iterates through news.json and transforms all hotlinked images
    into locally hosted, AI-reinterpreted versions.
    """
    if not os.path.exists(NEWS_FILE):
        print(f"Error: {NEWS_FILE} not found.")
        return

    with open(NEWS_FILE, 'r', encoding='utf-8') as f:
        news_data = json.load(f)

    updated_count = 0
    total = len(news_data)
    
    print(f"Starting bulk reprocessing of {total} articles...")

    for i, item in enumerate(news_data):
        article_id = item.get('id')
        current_image = item.get('image', '')
        title = item.get('title', '')

        # Process only if it's a remote URL (hotlink)
        if current_image.startswith('http'):
            print(f"[{i+1}/{total}] Processing {article_id}: {title[:50]}...")
            
            # Using the fidelity-tuned process_and_save_image from image_processor.py
            # This handles downloading, img2img transformation, and local saving.
            local_path = process_and_save_image(current_image, article_id, title)
            
            if local_path:
                item['image'] = local_path
                updated_count += 1
                
                # Intermediate save every 5 items to prevent data loss
                if updated_count % 5 == 0:
                    save_news(news_data)
            else:
                print(f"Skipping {article_id}: Transformation failed or returned None.")

    # Final save
    save_news(news_data)
    print(f"Reprocessing complete. Updated {updated_count} images.")

def save_news(data):
    with open(NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("News database updated.")

if __name__ == "__main__":
    reprocess_all_images()
