"""
Backfill de noticias no reescritas.
Busca en news.json las noticias con "rewritten": false y las reprocesa.
Ejecutar manualmente: python scraper/backfill_rewrite.py
"""
import json
import os
import sys
import time

# Para poder importar desde la carpeta scraper
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from analyze_sentiment import rewrite_article

def backfill_rewrite():
    # Ruta al archivo de noticias (relativa a la raíz del proyecto)
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root_dir)
    news_file = 'data/news.json'

    if not os.path.exists(news_file):
        print(f"No se encontró {news_file}")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news = json.load(f)

    # Filtrar noticias que NO han sido reescritas (rewritten == false o ausente)
    # Excluir resúmenes del día que no necesitan reescritura
    to_rewrite = [
        item for item in news
        if not item.get('rewritten') and not item.get('is_summary')
    ]

    if not to_rewrite:
        print("Todas las noticias ya están reescritas. No hay nada que hacer.")
        return

    print(f"Encontradas {len(to_rewrite)} noticias sin reescribir. Iniciando backfill...\n")

    ok_count = 0
    fail_count = 0

    for i, item in enumerate(to_rewrite, start=1):
        # Usar siempre el original para evitar reescribir sobre basura
        title_orig = item.get('original_title') or item.get('title', '')
        body_orig = item.get('original_body') or item.get('body', '')
        url = item.get('url', 'URL desconocida')

        if not title_orig or not body_orig:
            print(f"[{i}/{len(to_rewrite)}] SALTADA (sin título o cuerpo): {url}")
            fail_count += 1
            continue

        print(f"[{i}/{len(to_rewrite)}] Reescribiendo: {url}")

        try:
            new_title, new_body = rewrite_article(title_orig, body_orig)

            if new_title and new_body and (new_title != title_orig or new_body != body_orig):
                # Guardar originales si no existen
                if 'original_title' not in item:
                    item['original_title'] = title_orig
                if 'original_body' not in item:
                    item['original_body'] = body_orig

                item['title'] = new_title
                item['body'] = new_body
                item['rewritten'] = True
                ok_count += 1
                print(f"  [OK] Reescrita con éxito.")
            else:
                fail_count += 1
                print(f"  [FALLÓ] El modelo devolvió contenido vacío o idéntico al original.")

        except Exception as e:
            fail_count += 1
            print(f"  [ERROR] {e}")

        # Guardar progresivamente cada 3 noticias para no perder avance
        if i % 3 == 0:
            with open(news_file, 'w', encoding='utf-8') as f:
                json.dump(news, f, indent=2, ensure_ascii=False)
            print(f"  --- Progreso guardado ({i}/{len(to_rewrite)}) ---")

        # Delay entre noticias para respetar los rate limits de Groq
        time.sleep(2.0)

    # Guardado final
    with open(news_file, 'w', encoding='utf-8') as f:
        json.dump(news, f, indent=2, ensure_ascii=False)

    print(f"\nBackfill completado: {ok_count} reescritas, {fail_count} fallidas.")


if __name__ == "__main__":
    backfill_rewrite()
