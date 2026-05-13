import json
import os

def fix_religious_sentiment():
    news_file = 'data/news.json'
    if not os.path.exists(news_file):
        print("No se encontró news.json")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news = json.load(f)

    keywords = ['iglesia', 'cura', 'obispo', 'religioso', 'religiosa', 'papa', 'vaticano', 'misa', 'católico', 'cofradía', 'sacerdote', 'misionero']
    
    count = 0
    for item in news:
        text = (item.get('title', '') + " " + item.get('body', '') + " " + item.get('original_title', '')).lower()
        
        if any(k in text for k in keywords):
            if item.get('sentiment') != -0.8:
                print(f"Marcando como negativa (Religión): {item.get('title')}")
                item['sentiment'] = -0.8
                count += 1

    with open(news_file, 'w', encoding='utf-8') as f:
        json.dump(news, f, indent=2, ensure_ascii=False)
    
    print(f"Se han actualizado {count} noticias religiosas.")

if __name__ == "__main__":
    fix_religious_sentiment()
