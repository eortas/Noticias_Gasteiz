import json
import os

def deduplicate_news():
    news_file = 'data/news.json'
    if not os.path.exists(news_file):
        print("news.json not found")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news = json.load(f)

    seen_urls = set()
    seen_original_titles = set()
    unique_news = []
    
    # Procesamos al revés para quedarnos con la versión más reciente
    for item in reversed(news):
        url = item.get('url')
        orig_title = item.get('original_title')
        
        # Saltamos si ya vimos la URL
        if url in seen_urls:
            print(f"Eliminando duplicado por URL: {item.get('title')} ({url})")
            continue
            
        # Saltamos si ya vimos el título original (mismo contenido, distinta URL)
        if orig_title and orig_title in seen_original_titles:
            print(f"Eliminando duplicado por Título Original: {item.get('title')} ({orig_title})")
            continue
            
        unique_news.append(item)
        seen_urls.add(url)
        if orig_title:
            seen_original_titles.add(orig_title)

    # Volvemos a poner el orden original
    unique_news.reverse()

    with open(news_file, 'w', encoding='utf-8') as f:
        json.dump(unique_news, f, indent=2, ensure_ascii=False)
    
    print(f"Deduplicación completada. Antes: {len(news)}, Ahora: {len(unique_news)}")

if __name__ == "__main__":
    deduplicate_news()
