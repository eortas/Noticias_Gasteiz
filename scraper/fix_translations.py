import os
import json
import time
import sys
from deep_translator import GoogleTranslator

# Aseguramos que el script pueda encontrar el módulo scraper
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

def is_untranslated(original, translated):
    if not translated:
        return True
    # Si el texto traducido es idéntico al original (y tiene cierta longitud), 
    # es probable que haya fallado la traducción y se haya usado el original como fallback
    if len(original) > 50 and original.strip() == translated.strip():
        return True
    return False

def translate_with_google(text, target_lang):
    """Traducción simple usando Google Translate."""
    try:
        translator = GoogleTranslator(source='es', target=target_lang)
        if len(text) < 4500:
            return translator.translate(text)
        else:
            # Dividir en párrafos si es muy largo
            paragraphs = text.split('\n')
            translated_paragraphs = []
            current_chunk = ""
            for p in paragraphs:
                if len(current_chunk) + len(p) < 4000:
                    current_chunk += p + "\n"
                else:
                    translated_paragraphs.append(translator.translate(current_chunk))
                    current_chunk = p + "\n"
            if current_chunk:
                translated_paragraphs.append(translator.translate(current_chunk))
            return "\n".join(translated_paragraphs)
    except Exception as e:
        print(f"    ! Error en Google Translate ({target_lang}): {e}")
        return None

def main():
    news_file = 'data/news.json'
    if not os.path.exists(news_file):
        print(f"Error: {news_file} no existe.")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news = json.load(f)

    print(f"Revisando {len(news)} noticias en busca de traducciones faltantes...")
    print("Usando Google Translate para reparaciones (más estable para volumen alto).")
    
    modified = False
    count_eu = 0
    count_pl = 0

    for i, item in enumerate(news):
        title_es = item.get('title', '')
        body_es = item.get('body', '')
        
        if not title_es or not body_es:
            continue

        needs_eu = is_untranslated(body_es, item.get('body_eu'))
        needs_pl = is_untranslated(body_es, item.get('body_pl'))

        if needs_eu or needs_pl:
            print(f"[{i+1}/{len(news)}] Reparando: {title_es[:50]}...")
            
            if needs_eu:
                print("  - Traduciendo a Euskara (Google)...")
                t_eu = translate_with_google(title_es, 'eu')
                b_eu = translate_with_google(body_es, 'eu')
                if t_eu and b_eu:
                    item['title_eu'] = t_eu
                    item['body_eu'] = b_eu
                    count_eu += 1
                    modified = True

            if needs_pl:
                print("  - Traduciendo a Polaco (Google)...")
                t_pl = translate_with_google(title_es, 'pl')
                b_pl = translate_with_google(body_es, 'pl')
                if t_pl and b_pl:
                    item['title_pl'] = t_pl
                    item['body_pl'] = b_pl
                    count_pl += 1
                    modified = True
            
            if modified:
                with open(news_file, 'w', encoding='utf-8') as f:
                    json.dump(news, f, indent=2, ensure_ascii=False)
                print(f"  [OK] Progreso guardado.")
                modified = False
            
            # Pequeño respiro entre noticias
            time.sleep(1)

    print(f"\nFinalizado. Reparadas: {count_eu} Euskara, {count_pl} Polaco.")

if __name__ == "__main__":
    main()
