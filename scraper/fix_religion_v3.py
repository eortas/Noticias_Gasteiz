import json
import os
import re

def fix_religious_sentiment_v3():
    news_file = 'data/news.json'
    if not os.path.exists(news_file):
        print("No se encontró news.json")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news = json.load(f)

    keywords = [
        'iglesia', 'cura', 'curas', 'obispo', 'obispos', 'religioso', 'religiosa', 'papa', 
        'vaticano', 'misa', 'católico', 'cofradía', 'sacerdote', 'misionero', 
        'peregrinación', 'peregrinar', 'diócesis', 'estíbaliz'
    ]
    pattern = re.compile(r'\b(' + '|'.join(keywords) + r')\b', re.IGNORECASE)
    
    count = 0
    for item in news:
        text = (item.get('title', '') + " " + item.get('body', '') + " " + item.get('original_title', '')).lower()
        
        if pattern.search(text):
            if item.get('sentiment') != -0.8:
                print(f"Marcando como negativa (Religión/Peregrinación): {item.get('title')}")
                item['sentiment'] = -0.8
                count += 1

    with open(news_file, 'w', encoding='utf-8') as f:
        json.dump(news, f, indent=2, ensure_ascii=False)
    
    print(f"Se han actualizado {count} noticias con los nuevos criterios.")

if __name__ == "__main__":
    fix_religious_sentiment_v3()
