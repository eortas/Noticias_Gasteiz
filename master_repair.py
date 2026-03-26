import json
import os
import time
import sys
sys.path.append(os.path.join(os.getcwd(), 'scraper'))
from analyze_sentiment import translate_to_euskara, translate_to_polish, rewrite_article
from dotenv import load_dotenv

load_dotenv()

def master_repair():
    news_file = 'data/news.json'
    if not os.path.exists(news_file):
        print("No se encontró data/news.json")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news_data = json.load(f)

    total = len(news_data)
    print(f"Iniciando reparación maestra de {total} artículos...")

    any_change = False
    for i, article in enumerate(news_data):
        changed = False
        source_title = article.get('title', '')
        source_body = article.get('body', '')
        
        # 1. Euskara
        if not article.get('title_eu') or not article.get('body_eu'):
            print(f"[{i+1}/{total}] Reparando EUSKARA: {source_title[:40]}...")
            title_eu, body_eu = translate_to_euskara(source_title, source_body)
            if title_eu and body_eu:
                article['title_eu'] = title_eu
                article['body_eu'] = body_eu
                changed = True
                print("   ✓ EU Fix")
            time.sleep(2)

        # 2. Polish
        if not article.get('title_pl') or not article.get('body_pl'):
            print(f"[{i+1}/{total}] Reparando POLACO: {source_title[:40]}...")
            title_pl, body_pl = translate_to_polish(source_title, source_body)
            if title_pl and body_pl:
                article['title_pl'] = title_pl
                article['body_pl'] = body_pl
                changed = True
                print("   ✓ PL Fix")
            time.sleep(2)

        # 3. Rewrite (si no es ya un rewrite o fuente EU)
        if not article.get('body_rw') and not article.get('is_rewritten') and article.get('lang') != 'eu':
            print(f"[{i+1}/{total}] Reparando REWRITE: {source_title[:40]}...")
            title_rw, body_rw = rewrite_article(source_title, source_body)
            if title_rw and body_rw:
                article['title'] = title_rw
                article['body'] = body_rw
                article['is_rewritten'] = True
                changed = True
                print("   ✓ RW Fix")
            time.sleep(2)

        if changed:
            any_change = True
            # Guardamos cada cambio para seguridad
            with open(news_file, 'w', encoding='utf-8') as f:
                json.dump(news_data, f, indent=2, ensure_ascii=False)

    if not any_change:
        print("No se encontraron huecos que reparar.")
    else:
        print("Reparación completada.")

if __name__ == "__main__":
    master_repair()
