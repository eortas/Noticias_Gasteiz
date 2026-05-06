import os
import json
import time
import sys

# Aseguramos que el script pueda encontrar el módulo scraper
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

try:
    from analyze_sentiment import translate_to_euskara, translate_to_polish
except ImportError:
    from scraper.analyze_sentiment import translate_to_euskara, translate_to_polish

def is_untranslated(original, translated):
    if not translated:
        return True
    # Si el texto traducido es idéntico al original (y tiene cierta longitud), 
    # es probable que haya fallado la traducción y se haya usado el original como fallback
    if len(original) > 50 and original.strip() == translated.strip():
        return True
    return False

def main():
    news_file = 'data/news.json'
    if not os.path.exists(news_file):
        print(f"Error: {news_file} no existe.")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news = json.load(f)

    print(f"Revisando {len(news)} noticias en busca de traducciones faltantes...")
    
    modified = False
    count_eu = 0
    count_pl = 0

    # Procesar de más reciente a más antigua (normalmente el orden en el JSON)
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
                print("  - Traduciendo a Euskara...")
                t_eu, b_eu = translate_to_euskara(title_es, body_es)
                if t_eu and b_eu and not is_untranslated(body_es, b_eu):
                    item['title_eu'] = t_eu
                    item['body_eu'] = b_eu
                    count_eu += 1
                    modified = True
                else:
                    print("    ! Fallo en traducción a Euskara.")

            if needs_pl:
                print("  - Traduciendo a Polaco...")
                # Pequeño delay para no saturar API
                time.sleep(2)
                t_pl, b_pl = translate_to_polish(title_es, body_es)
                if t_pl and b_pl and not is_untranslated(body_es, b_pl):
                    item['title_pl'] = t_pl
                    item['body_pl'] = b_pl
                    count_pl += 1
                    modified = True
                else:
                    print("    ! Fallo en traducción a Polaco.")
            
            # Guardar progreso cada noticia reparada para evitar perder trabajo si falla
            if modified:
                with open(news_file, 'w', encoding='utf-8') as f:
                    json.dump(news, f, indent=2, ensure_ascii=False)
                print(f"  ✓ Progreso guardado.")
                modified = False # Reset flag for next check
            
            # Cooldown entre noticias para evitar rate limits (TPM)
            time.sleep(3)

    print(f"\nFinalizado. Reparadas: {count_eu} Euskara, {count_pl} Polaco.")

if __name__ == "__main__":
    main()
