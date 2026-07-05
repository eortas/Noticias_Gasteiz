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

    # Identificar noticias que:
    # 1. No tienen 'translated_eu'
    # 2. Tienen 'translated_eu' pero no tienen title_eu o body_eu
    # 3. Tienen 'translated_eu' pero body_eu es idéntico a body (lo que significa que se aplicó el fallback en castellano)
    to_retranslate = []
    for item in news:
        if item.get('is_summary'): 
            continue  # Omitir resumenes del día si aplica, o podemos incluirlos si lo deseas. Por ahora, omitimos.
            
        title = item.get('title', '')
        body = item.get('body', '')
        title_eu = item.get('title_eu', '')
        body_eu = item.get('body_eu', '')
        
        # Detectar si no está traducida o si la traducción es un fallback del texto original en castellano
        needs_translation = False
        if not item.get('translated_eu'):
            needs_translation = True
        elif not title_eu or not body_eu:
            needs_translation = True
        elif body_eu == body and len(body) > 100:  # Si el cuerpo traducido es idéntico al original en castellano
            needs_translation = True
            
        if needs_translation:
            to_retranslate.append(item)

    total = len(to_retranslate)
    if total == 0:
        print("Todas las noticias ya están correctamente traducidas al euskera.")
        return

    print(f"Detectadas {total} noticias con traducción pendiente o incompleta en euskera.")
    print("Iniciando traducción secuencial controlada para respetar el TPM de 8000 en Groq...")

    processed_count = 0
    for item in to_retranslate:
        url = item.get('url', 'URL desconocida')
        title_cast = item.get('title', '')
        body_cast = item.get('body', '')
        
        processed_count += 1
        print(f"\n[{processed_count}/{total}] Traduciendo: {url}")
        
        try:
            # Traducir título y cuerpo
            title_eu, body_eu = translate_article(title_cast, body_cast)
            
            if title_eu and body_eu and body_eu != body_cast:
                item['title_eu'] = title_eu
                item['body_eu'] = body_eu
                item['translated_eu'] = True
                print(f"  [OK] Traducido con éxito.")
            else:
                print(f"  [FALLÓ] La traducción devolvió un resultado no válido o vacío (posible fallback).")
                
            # Guardar progresivamente después de cada noticia para no perder avance
            with open(news_file, 'w', encoding='utf-8') as f:
                json.dump(news, f, indent=2, ensure_ascii=False)
                
            # Sleep obligatorio de 4 segundos entre noticias para mantenerse por debajo del límite de 8,000 TPM de Groq
            # (Un cuerpo de 600 palabras tarda unos 1.5s entre fragmentos, este delay extra asegura que el TPM se disipe).
            time.sleep(4.0)
            
        except Exception as e:
            print(f"  Error al procesar la noticia: {e}")
            time.sleep(5.0)

    print("\nProceso de traducción corrector finalizado con éxito.")

if __name__ == "__main__":
    retranslate_missing_news()
