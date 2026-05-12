import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from analyze_sentiment import rewrite_article

def reprocess_all_news(max_workers=8):
    news_file = 'data/news.json'
    if not os.path.exists(news_file):
        print(f"No se encontró {news_file}")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news = json.load(f)

    total = len(news)
    print(f"Iniciando REPROCESAMIENTO total de {total} noticias con {max_workers} hilos...", flush=True)
    print("Usando los textos originales para garantizar la máxima calidad con el nuevo motor.", flush=True)

    def process_item(item):
        # Intentar usar el original si existe, si no, el actual
        title_source = item.get('original_title') or item.get('title', '')
        body_source = item.get('original_body') or item.get('body', '')
        url = item.get('url', 'URL desconocida')

        if not title_source or not body_source:
            return False

        try:
            new_title, new_body = rewrite_article(title_source, body_source)
            
            if new_title and new_body:
                # Guardar originales si no estaban (por si acaso)
                if 'original_title' not in item:
                    item['original_title'] = title_source
                if 'original_body' not in item:
                    item['original_body'] = body_source
                
                item['title'] = new_title
                item['body'] = new_body
                item['rewritten'] = True
                return True
            return False
        except Exception as e:
            print(f"Error procesando {url}: {e}", flush=True)
            return False

    processed_count = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_item, item): item for item in news}
        
        for future in as_completed(futures):
            item = futures[future]
            success = future.result()
            processed_count += 1
            
            status = "OK" if success else "FALLÓ"
            print(f"[{processed_count}/{total}] {status}: {item.get('url')}", flush=True)
            
            if processed_count % 10 == 0:
                with open(news_file, 'w', encoding='utf-8') as f:
                    json.dump(news, f, indent=2, ensure_ascii=False)
                print(f"--- Sincronización intermedia ({processed_count}/{total}) ---", flush=True)

    with open(news_file, 'w', encoding='utf-8') as f:
        json.dump(news, f, indent=2, ensure_ascii=False)
    
    print(f"\nReprocesamiento completado. {processed_count} noticias actualizadas con el nuevo motor.", flush=True)

if __name__ == "__main__":
    # Usamos 8 workers para ir rápido con las 9 keys disponibles
    reprocess_all_news(max_workers=8)
