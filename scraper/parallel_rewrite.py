import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from analyze_sentiment import rewrite_article

def parallel_rewrite_news(max_workers=6):
    news_file = 'data/news.json'
    if not os.path.exists(news_file):
        print(f"No se encontró {news_file}")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news = json.load(f)

    # Filtrar solo las que no han sido reescritas aún
    # Consideramos "reescrita" si ya tiene el campo 'rewritten': true
    to_process = [item for item in news if not item.get('rewritten')]
    
    if not to_process:
        print("Todas las noticias ya están reescritas.")
        return

    total = len(to_process)
    print(f"Iniciando reescritura paralela de {total} noticias con {max_workers} hilos...", flush=True)

    def process_item(item):
        # Priorizar siempre los originales si ya existen para evitar reescribir sobre reescrito
        title_orig = item.get('original_title') or item.get('title', '')
        body_orig = item.get('original_body') or item.get('body', '')
        url = item.get('url', 'URL desconocida')

        if not title_orig or not body_orig:
            return None

        try:
            # Reescritura usando el pool de Groq (rotación aleatoria interna)
            new_title, new_body = rewrite_article(title_orig, body_orig)
            
            if new_title and new_body:
                # Guardar originales por si acaso
                if 'original_title' not in item:
                    item['original_title'] = title_orig
                if 'original_body' not in item:
                    item['original_body'] = body_orig
                
                item['title'] = new_title
                item['body'] = new_body
                item['rewritten'] = True
                return True
            else:
                return False
        except Exception as e:
            print(f"Error procesando {url}: {e}", flush=True)
            return False

    processed_count = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_item, item): item for item in to_process}
        
        for future in as_completed(futures):
            item = futures[future]
            success = future.result()
            processed_count += 1
            
            status = "OK" if success else "FALLÓ"
            print(f"[{processed_count}/{total}] {status}: {item.get('url')}", flush=True)
            
            # Guardar cada 5 finalizados para no perder progreso
            if processed_count % 5 == 0:
                with open(news_file, 'w', encoding='utf-8') as f:
                    json.dump(news, f, indent=2, ensure_ascii=False)
                print(f"--- Progreso guardado ({processed_count}/{total}) ---", flush=True)

    # Guardado final
    with open(news_file, 'w', encoding='utf-8') as f:
        json.dump(news, f, indent=2, ensure_ascii=False)
    
    print(f"\nProceso completado. {processed_count} noticias procesadas.", flush=True)

if __name__ == "__main__":
    # Usamos 6 workers como pidió el usuario (basado en sus 6 keys)
    parallel_rewrite_news(max_workers=6)
