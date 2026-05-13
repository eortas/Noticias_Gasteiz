import json
import os
import re

def fix_religious_sentiment_v2():
    news_file = 'data/news.json'
    if not os.path.exists(news_file):
        print("No se encontró news.json")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news = json.load(f)

    # Solo palabras completas
    keywords = ['iglesia', 'cura', 'curas', 'obispo', 'obispos', 'religioso', 'religiosa', 'papa', 'vaticano', 'misa', 'católico', 'cofradía', 'sacerdote', 'misionero']
    pattern = re.compile(r'\b(' + '|'.join(keywords) + r')\b', re.IGNORECASE)
    
    count_fixed = 0
    count_reverted = 0
    for item in news:
        text = (item.get('title', '') + " " + item.get('body', '') + " " + item.get('original_title', '')).lower()
        
        has_religion = bool(pattern.search(text))
        current_sentiment = item.get('sentiment')

        if has_religion:
            if current_sentiment != -0.8:
                print(f"Marcando como negativa (Religión): {item.get('title')}")
                item['sentiment'] = -0.8
                count_fixed += 1
        else:
            # Si se marcó como -0.8 pero NO tiene la palabra completa (fue un falso positivo)
            # Revertimos a neutral (o lo que fuera, pero neutral es seguro)
            # Solo si el título no menciona Guardia Civil
            if current_sentiment == -0.8 and 'guardia civil' not in text:
                print(f"Revirtiendo falso positivo: {item.get('title')}")
                item['sentiment'] = 0.0 # Neutral
                count_reverted += 1

    with open(news_file, 'w', encoding='utf-8') as f:
        json.dump(news, f, indent=2, ensure_ascii=False)
    
    print(f"Resumen: {count_fixed} fijados, {count_reverted} revertidos.")

if __name__ == "__main__":
    fix_religious_sentiment_v2()
