import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from analyze_sentiment import (
    analyze_sentiment,
    is_headline_rewritten,
    rewrite_article,
    rewrite_headline,
    translate_article,
    translate_article_to_languages,
)

def parallel_rewrite_news(max_workers=2, max_batch=20):
    news_file = 'data/news.json'
    if not os.path.exists(news_file):
        print(f"No se encontró {news_file}")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news = json.load(f)

    # Identificamos noticias pendientes de reescritura, traducción o con titular no modificado
    to_process = []
    for item in news:
        original_title = item.get('original_title')
        current_title = item.get('title', '')
        title_needs_rewrite = bool(
            original_title
            and not is_headline_rewritten(original_title, current_title)
        )

        needs_any_translation = not (
            item.get('translated_eu')
            and item.get('translated_pl')
            and item.get('translated_fr')
            and item.get('translated_en')
        )

        if not item.get('rewritten') or needs_any_translation or title_needs_rewrite:
            to_process.append(item)
    
    if not to_process:
        print("Todas las noticias ya están reescritas y traducidas.")
        return

    # Si hay acumulación extraordinaria, limitamos al lote máximo para garantizar la finalización dentro de la ventana de 20 minutos
    if len(to_process) > max_batch:
        print(f"Detectadas {len(to_process)} noticias pendientes. Limitamos a un lote de {max_batch} para mantener el ciclo en unos 5-7 minutos.")
        to_process = to_process[:max_batch]

    total = len(to_process)
    print(f"Iniciando reescritura/traducción paralela de {total} noticias con {max_workers} hilos...", flush=True)

    def process_item(item):
        # Priorizamos originales para evitar reescribir sobre reescrito
        title_orig = item.get('original_title') or item.get('title', '')
        body_orig = item.get('original_body') or item.get('body', '')
        url = item.get('url', 'URL desconocida')

        if not title_orig or not body_orig:
            return None

        success = False
        try:
            # 1. Reescribir en castellano si no se ha hecho
            if not item.get('rewritten'):
                new_title, new_body = rewrite_article(title_orig, body_orig)
                if new_title and new_body:
                    if 'original_title' not in item:
                        item['original_title'] = title_orig
                    if 'original_body' not in item:
                        item['original_body'] = body_orig
                    
                    item['title'] = new_title
                    item['body'] = new_body
                    
                    # Recalculamos el sentimiento sobre el texto limpio y reescrito
                    _label, new_score, _cat = analyze_sentiment(new_title + " " + new_body)
                    item['sentiment'] = round(new_score, 4)
                    
                    if new_title != title_orig or new_body != body_orig:
                        item['rewritten'] = True
                    else:
                        item['rewritten'] = False
                    success = True
                else:
                    return False
            else:
                # Si el cuerpo ya estaba reescrito, corregimos solo el titular idéntico
                if item.get('original_title') and not is_headline_rewritten(
                    title_orig,
                    item.get('title', ''),
                ):
                    new_title = rewrite_headline(title_orig)
                    if not is_headline_rewritten(title_orig, new_title):
                        print(f"El titular sigue sin reescribirse: {url}", flush=True)
                        return False

                    item['title'] = new_title
                    _label, new_score, _cat = analyze_sentiment(
                        new_title + " " + item.get('body', '')
                    )
                    item['sentiment'] = round(new_score, 4)

                success = True

            current_title = item.get('title', '')
            current_body = item.get('body', '')

            # 2. Identificamos qué idiomas faltan por traducir
            target_langs = []
            if not item.get('translated_eu'):
                target_langs.append('eu')
            if not item.get('translated_pl'):
                target_langs.append('pl')
            if not item.get('translated_fr'):
                target_langs.append('fr')
            if not item.get('translated_en'):
                target_langs.append('en')

            # Traducimos concurrentemente todos los idiomas pendientes
            if success and target_langs:
                translations = translate_article_to_languages(
                    current_title, current_body, target_langs=target_langs
                )
                for lang in target_langs:
                    t_lang, b_lang = translations.get(lang, (None, None))
                    if t_lang and b_lang:
                        item[f'title_{lang}'] = t_lang
                        item[f'body_{lang}'] = b_lang
                        item[f'translated_{lang}'] = True
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
            
            # Guardamos cada 2 finalizados para asegurar el progreso sin sobrecargar el disco
            if processed_count % 2 == 0:
                with open(news_file, 'w', encoding='utf-8') as f:
                    json.dump(news, f, indent=2, ensure_ascii=False)
                print(f"--- Progreso guardado ({processed_count}/{total}) ---", flush=True)

    # Guardado final
    with open(news_file, 'w', encoding='utf-8') as f:
        json.dump(news, f, indent=2, ensure_ascii=False)
    
    print(f"\nProceso completado. {processed_count} noticias procesadas.", flush=True)

if __name__ == "__main__":
    # Procesamos de 2 en 2 artículos con traducciones multilingües concurrentes
    parallel_rewrite_news(max_workers=2, max_batch=20)
