import json
import os
import re

def global_sentiment_fix():
    news_file = 'data/news.json'
    if not os.path.exists(news_file):
        print("No se encontró news.json")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news = json.load(f)

    # Diccionario de palabras que SIEMPRE deben ser negativas
    neg_keywords = [
        'robo', 'detenido', 'agresión', 'pelea', 'herido', 'denuncia', 'huelga', 'incendio', 
        'atropello', 'crimen', 'estafa', 'muerte', 'fallece', 'asesinato', 'asesino', 'juicio', 
        'fiscalía', 'asalto', 'asaltan', 'extorsión', 'maialen', 'jaime', 'guardia civil', 
        'iglesia', 'cura', 'obispo', 'religioso', 'peregrinación', 'diócesis', 'misa'
    ]
    pattern = re.compile(r'\b(' + '|'.join(neg_keywords) + r')\b', re.IGNORECASE)
    
    count = 0
    for item in news:
        text = (item.get('title', '') + " " + item.get('body', '') + " " + item.get('original_title', '')).lower()
        
        if pattern.search(text):
            # Forzamos negativo si no lo es o si es neutral
            if item.get('sentiment', 0) >= -0.05:
                print(f"Corrigiendo a NEGATIVA: {item.get('title')}")
                # Si es algo grave como asesinato, ponemos -1.0, si no -0.8
                if any(k in text for k in ['asesinato', 'muerte', 'crimen', 'maialen']):
                    item['sentiment'] = -1.0
                else:
                    item['sentiment'] = -0.8
                count += 1

    with open(news_file, 'w', encoding='utf-8') as f:
        json.dump(news, f, indent=2, ensure_ascii=False)
    
    print(f"Se han corregido {count} noticias a sentimiento negativo.")

if __name__ == "__main__":
    global_sentiment_fix()
