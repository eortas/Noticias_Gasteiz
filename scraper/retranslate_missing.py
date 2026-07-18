import json
import os
import sys
import time

# Agregar la carpeta actual al path para importar
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from analyze_sentiment import translate_article

def retranslate_missing_news():
    news_file = 'data/news.json'
    if not os.path.exists(news_file):
        print(f"No se encontró {news_file}")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news = json.load(f)

    # Identificar noticias que necesitan traducción
    to_retranslate = []
    for item in news:
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
        
        # Evaluar necesidades por idioma
        needs_eu = False
        if not item.get('translated_eu'):
            needs_eu = True
        elif not title_eu or not body_eu:
            needs_eu = True
        elif body_eu == body and len(body) > 100:
            needs_eu = True
            
        needs_pl = False
        if not item.get('translated_pl'):
            needs_pl = True
        elif not title_pl or not body_pl:
            needs_pl = True
        elif body_pl == body and len(body) > 100:
            needs_pl = True
            
        needs_fr = False
        if not item.get('translated_fr'):
            needs_fr = True
        elif not title_fr or not body_fr:
            needs_fr = True
        elif body_fr == body and len(body) > 100:
            needs_fr = True
            
        needs_en = False
        if not item.get('translated_en'):
            needs_en = True
        elif not title_en or not body_en:
            needs_en = True
        elif body_en == body and len(body) > 100:
            needs_en = True
            
        if needs_eu or needs_pl or needs_fr or needs_en:
            to_retranslate.append((item, needs_eu, needs_pl, needs_fr, needs_en))

    total = len(to_retranslate)
    if total == 0:
        print("Todas las noticias ya están correctamente traducidas al euskera, polaco, francés e inglés.")
        return

    # Si hay demasiadas noticias pendientes, limitamos para evitar bloqueos/esperas largas
    # Priorizamos todos los resúmenes y los últimos 15 artículos de noticias (más recientes)
    if total > 15:
        print(f"Detectadas {total} noticias con traducción pendiente.")
        print("Limitando a resúmenes y a los 15 artículos más recientes para agilizar el pipeline.")
        summaries = [x for x in to_retranslate if x[0].get('is_summary')]
        non_summaries = [x for x in to_retranslate if not x[0].get('is_summary')]
        to_retranslate = summaries + non_summaries[:15]
        total = len(to_retranslate)

    # Priorizar resúmenes para que se traduzcan en primer lugar
    to_retranslate.sort(key=lambda x: 0 if x[0].get('is_summary') else 1)

    print(f"Detectadas {total} noticias con traducción pendiente o incompleta.")
    print("Iniciando traducción secuencial controlada para respetar el TPM de 8000 en Groq...")

    processed_count = 0
    for item, needs_eu, needs_pl, needs_fr, needs_en in to_retranslate:
        url = item.get('url', 'URL de Resumen Diario/Especial')
        title_cast = item.get('title', '')
        body_cast = item.get('body', '')
        
        processed_count += 1
        langs_str = []
        if needs_eu: langs_str.append("Euskera")
        if needs_pl: langs_str.append("Polaco")
        if needs_fr: langs_str.append("Francés")
        if needs_en: langs_str.append("Inglés")
        print(f"\n[{processed_count}/{total}] Traduciendo a {', '.join(langs_str)}: {url}")
        
        try:
            # 1. Traducir al euskera si es necesario
            if needs_eu:
                title_eu, body_eu = translate_article(title_cast, body_cast, target_lang="eu")
                if title_eu and body_eu and body_eu != body_cast:
                    item['title_eu'] = title_eu
                    item['body_eu'] = body_eu
                    item['translated_eu'] = True
                    print(f"  [Euskera - OK] Traducido con éxito.")
                else:
                    print(f"  [Euskera - FALLÓ] Resultado vacío o fallback en castellano.")
                time.sleep(1.0) # Separación preventiva
                
            # 2. Traducir al polaco si es necesario
            if needs_pl:
                title_pl, body_pl = translate_article(title_cast, body_cast, target_lang="pl")
                if title_pl and body_pl and body_pl != body_cast:
                    item['title_pl'] = title_pl
                    item['body_pl'] = body_pl
                    item['translated_pl'] = True
                    print(f"  [Polaco - OK] Traducido con éxito.")
                else:
                    print(f"  [Polaco - FALLÓ] Resultado vacío o fallback en castellano.")
                time.sleep(1.0)
                
            # 3. Traducir al francés si es necesario
            if needs_fr:
                title_fr, body_fr = translate_article(title_cast, body_cast, target_lang="fr")
                if title_fr and body_fr and body_fr != body_cast:
                    item['title_fr'] = title_fr
                    item['body_fr'] = body_fr
                    item['translated_fr'] = True
                    print(f"  [Francés - OK] Traducido con éxito.")
                else:
                    print(f"  [Francés - FALLÓ] Resultado vacío o fallback en castellano.")
                time.sleep(1.0)
                
            # 4. Traducir al inglés si es necesario
            if needs_en:
                title_en, body_en = translate_article(title_cast, body_cast, target_lang="en")
                if title_en and body_en and body_en != body_cast:
                    item['title_en'] = title_en
                    item['body_en'] = body_en
                    item['translated_en'] = True
                    print(f"  [Inglés - OK] Traducido con éxito.")
                else:
                    print(f"  [Inglés - FALLÓ] Resultado vacío o fallback en castellano.")
                    
            # Guardar progresivamente después de cada noticia para no perder avance
            with open(news_file, 'w', encoding='utf-8') as f:
                json.dump(news, f, indent=2, ensure_ascii=False)
                
            # Sleep de cortesía entre noticias; el retry gestiona rate limits reales
            time.sleep(1.5)
            
        except Exception as e:
            print(f"  Error al procesar la noticia: {e}")
            time.sleep(2.0)

    print("\nProceso de traducción corrector finalizado con éxito.")

if __name__ == "__main__":
    retranslate_missing_news()
