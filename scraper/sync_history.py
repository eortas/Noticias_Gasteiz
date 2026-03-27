import json
import os

def sync():
    news_file = 'data/news.json'
    history_file = 'scraper/history.json'
    
    if not os.path.exists(news_file):
        print("No news.json found.")
        return
        
    with open(news_file, 'r', encoding='utf-8') as f:
        news = json.load(f)
        
    urls = [item['url'] for item in news if 'url' in item]
    
    existing_history = []
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            existing_history = json.load(f)
            
    # Combine and dedup
    new_history = list(set(existing_history + urls))
    
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(new_history, f, indent=4)
        
    print(f"History synced: {len(new_history)} URLs in history.")

if __name__ == "__main__":
    sync()
