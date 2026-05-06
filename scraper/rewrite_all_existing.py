import json
import os
import time
from analyze_sentiment import rewrite_article

def rewrite_all_existing():
    news_file = 'data/news.json'
    if not os.path.exists(news_file):
        print(f"No se encontró {news_file}")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news = json.load(f)

    total = len(news)
    print(f"Iniciando reescritura masiva de {total} noticias con el nuevo sistema...")

    for i, item in enumerate(news):
        title_orig = item.get('title', '')
        body_orig = item.get('body', '')
        url = item.get('url', 'URL desconocida')

        if not title_orig or not body_orig:
            continue

        print(f"[{i+1}/{total}] Re-escribiendo: {url}")
        
        try:
            # Aplicar el nuevo sistema de reescritura
            new_title, new_body = rewrite_article(title_orig, body_orig)
            
            if new_title and new_body:
                item['title'] = new_title
                item['body'] = new_body
                print("  OK: Reescribido.")
            else:
                print("  ERROR: Error en la API, manteniendo original.")
        except Exception as e:
            print(f"  EXCEPTION: {e}")

        # Guardar cada 5 noticias para no perder progreso
        if (i + 1) % 5 == 0:
            with open(news_file, 'w', encoding='utf-8') as f:
                json.dump(news, f, indent=2, ensure_ascii=False)
            print(f"--- Progreso guardado ({i+1}/{total}) ---")
        
        # Pequeño cooldown para evitar límites de la API
        time.sleep(1)

    # Guardado final
    with open(news_file, 'w', encoding='utf-8') as f:
        json.dump(news, f, indent=2, ensure_ascii=False)
    
    print("\nProceso de reescritura completado.")

if __name__ == "__main__":
    rewrite_all_existing()
