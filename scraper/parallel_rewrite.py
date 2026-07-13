import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from analyze_sentiment import rewrite_article, translate_article

def parallel_rewrite_news(max_workers=6):
    news_file = 'data/news.json'
    if not os.path.exists(news_file):
        print(f"No se encontró {news_file}")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news = json.load(f)

    # Filtrar las noticias que no han sido reescritas aún O no han sido traducidas al euskera aún
    to_process = [item for item in news if not item.get('rewritten') or not item.get('translated_eu')]
    
    if not to_process:
        print("Todas las noticias ya están reescritas y traducidas.")
        return

    total = len(to_process)
    print(f"Iniciando reescritura/traducción paralela de {total} noticias con {max_workers} hilos...", flush=True)

    def process_item(item):
        # Priorizar siempre los originales si ya existen para evitar reescribir sobre reescrito
        title_orig = item.get('original_title') or item.get('title', '')
        body_orig = item.get('original_body') or item.get('body', '')
        url = item.get('url', 'URL desconocida')

        if not title_orig or not body_orig:
            return None

        success = False
        try:
            # 1. Reescribir si no se ha hecho
            if not item.get('rewritten'):
                new_title, new_body = rewrite_article(title_orig, body_orig)
                if new_title and new_body:
                    # Guardar originales por si acaso
                    if 'original_title' not in item:
                        item['original_title'] = title_orig
                    if 'original_body' not in item:
                        item['original_body'] = body_orig
                    
                    item['title'] = new_title
                    item['body'] = new_body
                    
                    # Marcamos como reescrita solo si realmente cambió respecto al original
                    if new_title != title_orig or new_body != body_orig:
                        item['rewritten'] = True
                    else:
                        item['rewritten'] = False
                    success = True
                else:
                    return False
            else:
                success = True # Ya estaba reescrita, procedemos con traducción

            # 2. Traducir al euskera si no se ha hecho
            if success and not item.get('translated_eu'):
                current_title = item.get('title', '')
                current_body = item.get('body', '')
                title_eu, body_eu = translate_article(current_title, current_body)
                if title_eu and body_eu:
                    item['title_eu'] = title_eu
                    item['body_eu'] = body_eu
                    item['translated_eu'] = True
                else:
                    success = False

            return success
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
