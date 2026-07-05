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
            
        if needs_eu or needs_pl:
            to_retranslate.append((item, needs_eu, needs_pl))

    total = len(to_retranslate)
    if total == 0:
        print("Todas las noticias ya están correctamente traducidas al euskera y al polaco.")
        return

    # Priorizar resúmenes para que se traduzcan en primer lugar
    to_retranslate.sort(key=lambda x: 0 if x[0].get('is_summary') else 1)

    print(f"Detectadas {total} noticias con traducción pendiente o incompleta.")
    print("Iniciando traducción secuencial controlada para respetar el TPM de 8000 en Groq...")

    processed_count = 0
    for item, needs_eu, needs_pl in to_retranslate:
        url = item.get('url', 'URL de Resumen Diario/Especial')
        title_cast = item.get('title', '')
        body_cast = item.get('body', '')
        
        processed_count += 1
        langs_str = []
        if needs_eu: langs_str.append("Euskera")
        if needs_pl: langs_str.append("Polaco")
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
                time.sleep(3.0) # Separación preventiva
                
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
                    
            # Guardar progresivamente después de cada noticia para no perder avance
            with open(news_file, 'w', encoding='utf-8') as f:
                json.dump(news, f, indent=2, ensure_ascii=False)
                
            # Sleep obligatorio entre noticias para mantenerse por debajo del límite de 8,000 TPM de Groq
            time.sleep(4.0)
            
        except Exception as e:
            print(f"  Error al procesar la noticia: {e}")
            time.sleep(5.0)

    print("\nProceso de traducción corrector finalizado con éxito.")

if __name__ == "__main__":
    retranslate_missing_news()
