import json
import os
import time
import sys
sys.path.append(os.path.join(os.getcwd(), 'scraper'))
from analyze_sentiment import rewrite_article
from dotenv import load_dotenv
from deep_translator import GoogleTranslator

load_dotenv()

def translate_with_google(text, target_lang):
    """Traducción simple usando Google Translate."""
    if not text:
        return ""
    try:
        translator = GoogleTranslator(source='auto', target=target_lang)
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

def translate_to_euskara(title, body):
    return translate_with_google(title, 'eu'), translate_with_google(body, 'eu')

def translate_to_polish(title, body):
    return translate_with_google(title, 'pl'), translate_with_google(body, 'pl')

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
        source_title = article.get('original_title') or article.get('title', '')
        source_body = article.get('original_body') or article.get('body', '')
        
        # 1. Euskara
        if not article.get('title_eu') or not article.get('body_eu'):
            print(f"[{i+1}/{total}] Reparando EUSKARA: {source_title[:40]}...")
            title_eu, body_eu = translate_to_euskara(source_title, source_body)
            if title_eu and body_eu:
                article['title_eu'] = title_eu
                article['body_eu'] = body_eu
                changed = True
                print("   [OK] EU Fix")
            time.sleep(1)

        # 2. Polish
        if not article.get('title_pl') or not article.get('body_pl'):
            print(f"[{i+1}/{total}] Reparando POLACO: {source_title[:40]}...")
            title_pl, body_pl = translate_to_polish(source_title, source_body)
            if title_pl and body_pl:
                article['title_pl'] = title_pl
                article['body_pl'] = body_pl
                changed = True
                print("   [OK] PL Fix")
            time.sleep(1)

        # 3. Rewrite (si no está reescrito aún)
        if not article.get('rewritten'):
            print(f"[{i+1}/{total}] Reparando REWRITE: {source_title[:40]}...")
            title_rw, body_rw = rewrite_article(source_title, source_body)
            if title_rw and body_rw:
                article['original_title'] = source_title
                article['original_body'] = source_body
                article['title'] = title_rw
                article['body'] = body_rw
                article['rewritten'] = True
                changed = True
                print("   [OK] RW Fix")
            time.sleep(1)

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
