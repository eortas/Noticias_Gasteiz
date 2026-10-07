import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

# Agregamos la carpeta actual al path para importar
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from analyze_sentiment import translate_article, translate_article_to_languages
except (ImportError, AttributeError):
    try:
        from analyze_sentiment import translate_article
    except ImportError:
        translate_article = None
    translate_article_to_languages = None

def retranslate_missing_news():
    news_file = 'data/news.json'
    if not os.path.exists(news_file):
        print(f"No se encontró {news_file}")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news = json.load(f)

    # Solo traducimos noticias de las últimas 24h para optimizar consumo
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)

    # Identificamos noticias recientes que necesitan traducción
    to_retranslate = []
    for item in news:
        try:
            date_value = item.get('date') or ''
            item_date = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            if item_date.tzinfo is None:
                item_date = item_date.replace(tzinfo=timezone.utc)
            if item_date < cutoff and not item.get('is_summary'):
                continue
        except (ValueError, TypeError):
            continue
        title = item.get('title', '')
        body = item.get('body', '')
        title_eu = item.get('title_eu', '')
        body_eu = item.get('body_eu', '')
        title_pl = item.get('title_pl', '')
        body_pl = item.get('body_pl', '')
        title_fr = item.get('title_fr', '')
        body_fr = item.get('body_fr', '')
        title_en = item.get('title_en', '')
        body_en = item.get('body_en', '')
        
        needs_eu = not item.get('translated_eu') or not title_eu or not body_eu or (body_eu == body and len(body) > 100)
        needs_pl = not item.get('translated_pl') or not title_pl or not body_pl or (body_pl == body and len(body) > 100)
        needs_fr = not item.get('translated_fr') or not title_fr or not body_fr or (body_fr == body and len(body) > 100)
        needs_en = not item.get('translated_en') or not title_en or not body_en or (body_en == body and len(body) > 100)
            
        if needs_eu or needs_pl or needs_fr or needs_en:
            to_retranslate.append((item, needs_eu, needs_pl, needs_fr, needs_en))

    total = len(to_retranslate)
    if total == 0:
        print("Todas las noticias ya están correctamente traducidas al euskera, polaco, francés e inglés.")
        return

    # Si hay demasiadas noticias pendientes, limitamos para agilizar el pipeline
    if total > 15:
        print(f"Detectadas {total} noticias con traducción pendiente.")
        print("Limitando a resúmenes y a los 15 artículos más recientes para agilizar el pipeline.")
        summaries = [x for x in to_retranslate if x[0].get('is_summary')]
        non_summaries = [x for x in to_retranslate if not x[0].get('is_summary')]
        to_retranslate = summaries + non_summaries[:15]
        total = len(to_retranslate)

    # Priorizamos resúmenes
    to_retranslate.sort(key=lambda x: 0 if x[0].get('is_summary') else 1)

    print(f"Detectadas {total} noticias con traducción pendiente o incompleta.")
    print("Iniciando traducción concurrente por artículo aprovechando pools dedicados de claves...")

    processed_count = 0
    for item, needs_eu, needs_pl, needs_fr, needs_en in to_retranslate:
        url = item.get('url', 'URL de Resumen Diario/Especial')
        title_cast = item.get('title', '')
        body_cast = item.get('body', '')
        
        processed_count += 1
        needed_langs = []
        if needs_eu: needed_langs.append("eu")
        if needs_pl: needed_langs.append("pl")
        if needs_fr: needed_langs.append("fr")
        if needs_en: needed_langs.append("en")

        print(f"\n[{processed_count}/{total}] Traduciendo a {', '.join(needed_langs)}: {url}")
        
        try:
            if translate_article_to_languages and len(needed_langs) > 0:
                translations = translate_article_to_languages(title_cast, body_cast, target_langs=needed_langs)
                for lang in needed_langs:
                    t_res, b_res = translations.get(lang, (None, None))
                    if t_res and b_res and b_res != body_cast:
                        item[f'title_{lang}'] = t_res
                        item[f'body_{lang}'] = b_res
                        item[f'translated_{lang}'] = True
                        print(f"  [{lang.upper()} - OK] Traducido con éxito.")
                    else:
                        print(f"  [{lang.upper()} - FALLÓ] Resultado vacío o fallback en castellano.")
            elif translate_article:
                # Fallback secuencial
                for lang in needed_langs:
                    t_res, b_res = translate_article(title_cast, body_cast, target_lang=lang)
                    if t_res and b_res and b_res != body_cast:
                        item[f'title_{lang}'] = t_res
                        item[f'body_{lang}'] = b_res
                        item[f'translated_{lang}'] = True
                        print(f"  [{lang.upper()} - OK] Traducido con éxito.")
                    else:
                        print(f"  [{lang.upper()} - FALLÓ] Resultado vacío o fallback en castellano.")
                    time.sleep(0.5)

            # Guardamos tras cada noticia
            with open(news_file, 'w', encoding='utf-8') as f:
                json.dump(news, f, indent=2, ensure_ascii=False)
                
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  Error al procesar la noticia: {e}")
            time.sleep(1.0)

    print("\nProceso de traducción corrector finalizado con éxito.")

if __name__ == "__main__":
    retranslate_missing_news()
