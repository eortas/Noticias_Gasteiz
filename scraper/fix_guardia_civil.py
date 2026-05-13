import json
import os

def fix_guardia_civil_sentiment():
    news_file = 'data/news.json'
    if not os.path.exists(news_file):
        print("No se encontró news.json")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news = json.load(f)

    count = 0
    for item in news:
        title = item.get('title', '').lower()
        body = item.get('body', '').lower()
        orig_title = item.get('original_title', '').lower()
        
        if 'guardia civil' in title or 'guardia civil' in body or 'guardia civil' in orig_title:
            print(f"Marcando como negativa: {item.get('title')}")
            item['sentiment'] = -0.8
            count += 1

    with open(news_file, 'w', encoding='utf-8') as f:
        json.dump(news, f, indent=2, ensure_ascii=False)
    
    print(f"Se han actualizado {count} noticias de la Guardia Civil.")

if __name__ == "__main__":
    fix_guardia_civil_sentiment()
