import json
import os
from datetime import datetime, timedelta, timezone

def cleanup_old_news():
    news_file = 'data/news.json'
    if not os.path.exists(news_file):
        print("No news.json found")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news = json.load(f)

    now = datetime.now(timezone.utc)
    # Ayer a las 00:00:00 UTC
    yesterday_start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    print(f"Limpiando noticias anteriores a {yesterday_start}...")
    
    filtered_news = []
    removed_count = 0
    
    for item in news:
        date_str = item.get('date')
        if not date_str:
            removed_count += 1
            continue
        try:
            # Handle ISO format
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            if dt >= yesterday_start:
                filtered_news.append(item)
            else:
                removed_count += 1
        except:
            removed_count += 1
            
    with open(news_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_news, f, indent=2, ensure_ascii=False)
        
    print(f"Limpieza completada. Eliminadas {removed_count} noticias antiguas. Quedan {len(filtered_news)}.")

if __name__ == "__main__":
    cleanup_old_news()
