import json
import os
import time
import sys
sys.path.append(os.path.join(os.getcwd(), 'scraper'))
from analyze_sentiment import translate_to_polish
from dotenv import load_dotenv

load_dotenv()

def backfill_polish():
    news_file = 'data/news.json'
    if not os.path.exists(news_file):
        print("No se encontró data/news.json")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news_data = json.load(f)

    total = len(news_data)
    print(f"Iniciando traducción al polaco de {total} artículos...")

    for i, article in enumerate(news_data):
        # Si ya tiene traducción al polaco, saltar (opcional, pero útil si se interrumpe)
        if article.get('title_pl') and article.get('body_pl'):
            continue

        print(f"[{i+1}/{total}] Traduciendo: {article.get('title')[:50]}...")
        
        # Usar el título original o corregido para la mejor traducción
        source_title = article.get('title', '')
        source_body = article.get('body', '')
        
        # Intentar traducir
        title_pl, body_pl = translate_to_polish(source_title, source_body)
        
        if title_pl and body_pl:
            article['title_pl'] = title_pl
            article['body_pl'] = body_pl
            print(f"   ✓ Éxito")
        else:
            print(f"   ✗ Fallo")

        # Guardar cada 5 para no perder progreso
        if (i + 1) % 5 == 0:
            with open(news_file, 'w', encoding='utf-8') as f:
                json.dump(news_data, f, indent=2, ensure_ascii=False)
            print(f"--- Progreso guardado ---")

        # Pequeño delay para evitar rate limits
        time.sleep(3)

    # Guardado final
    with open(news_file, 'w', encoding='utf-8') as f:
        json.dump(news_data, f, indent=2, ensure_ascii=False)
    
    print("Backfill de polaco completado.")

if __name__ == "__main__":
    backfill_polish()
