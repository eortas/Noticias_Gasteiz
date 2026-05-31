import json
import os
import re
from datetime import datetime
import urllib.parse

def tokenize(text):
    if not text:
        return set()
    stopwords = {
        'de', 'la', 'el', 'en', 'y', 'a', 'los', 'un', 'una', 'con', 'para', 'este', 'esta', 'por', 'del', 
        'al', 'se', 'las', 'su', 'sus', 'o', 'u', 'como', 'que', 'lo', 'uno', 'unas', 'unos',
        'correo', 'gasteiz', 'hoy', 'noticias', 'alava', 'vitoria', 'diario', 'araba', 'html', 'htm'
    }
    text = text.lower()
    text = re.sub(r'[.,\/#!$%\^&\*;:{}=\-_`~()?"\'\n\r0-9]', ' ', text)
    words = text.split()
    return {w for w in words if len(w) > 2 and w not in stopwords}

def jaccard_similarity(set_a, set_b):
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)

def get_source_priority(source):
    priorities = {
        'El Correo': 3,
        'Diario de Noticias': 2,
        'Gasteiz Hoy': 1
    }
    return priorities.get(source, 0)

def is_better_version(item_new, item_existing):
    # Prioridad 1: Imagen real vs sin imagen / placeholder / logo
    img_new = item_new.get('image') or ""
    img_exist = item_existing.get('image') or ""
    
    is_placeholder_new = not img_new or any(x in img_new.lower() for x in ['placeholder', 'logo', 'default'])
    is_placeholder_exist = not img_exist or any(x in img_exist.lower() for x in ['placeholder', 'logo', 'default'])
    
    if not is_placeholder_new and is_placeholder_exist:
        return True
    if is_placeholder_new and not is_placeholder_exist:
        return False
        
    # Prioridad 2: Fuente preferida
    prio_new = get_source_priority(item_new.get('source'))
    prio_exist = get_source_priority(item_existing.get('source'))
    if prio_new > prio_exist:
        return True
    if prio_new < prio_exist:
        return False
        
    # Prioridad 3: Cuerpo más completo
    return len(item_new.get('body', '')) > len(item_existing.get('body', ''))

def are_duplicates(item_a, item_b):
    if item_a.get('url') == item_b.get('url'):
        return True
        
    # Si son de fuentes distintas, no las eliminamos físicamente para que el frontend las agrupe
    if item_a.get('source') != item_b.get('source'):
        return False
        
    orig_a = item_a.get('original_title', '').strip().lower()
    orig_b = item_b.get('original_title', '').strip().lower()
    if orig_a and orig_b and orig_a == orig_b:
        return True
        
    title_a = item_a.get('title', '').strip().lower()
    title_b = item_b.get('title', '').strip().lower()
    if title_a and title_b and title_a == title_b:
        return True

    url_words_a = ""
    if item_a.get('url'):
        try:
            url_words_a = urllib.parse.urlparse(item_a['url']).path
        except Exception:
            url_words_a = item_a['url']
        url_words_a = re.sub(r'[\/\-_.]', ' ', url_words_a)
        url_words_a = re.sub(r'\d+', '', url_words_a)

    url_words_b = ""
    if item_b.get('url'):
        try:
            url_words_b = urllib.parse.urlparse(item_b['url']).path
        except Exception:
            url_words_b = item_b['url']
        url_words_b = re.sub(r'[\/\-_.]', ' ', url_words_b)
        url_words_b = re.sub(r'\d+', '', url_words_b)

    title_tokens_a = tokenize((item_a.get('title') or "") + " " + (item_a.get('original_title') or "") + " " + url_words_a)
    title_tokens_b = tokenize((item_b.get('title') or "") + " " + (item_b.get('original_title') or "") + " " + url_words_b)
    
    body_tokens_a = tokenize((item_a.get('body') or "") + " " + (item_a.get('original_body') or ""))
    body_tokens_b = tokenize((item_b.get('body') or "") + " " + (item_b.get('original_body') or ""))
    
    title_sim = jaccard_similarity(title_tokens_a, title_tokens_b)
    body_sim = jaccard_similarity(body_tokens_a, body_tokens_b)
    
    if title_sim >= 0.50:
        return True
    if body_sim >= 0.33:
        return True
    if title_sim >= 0.30 and body_sim >= 0.25:
        return True
        
    return False

def deduplicate_news():
    news_file = 'data/news.json'
    if not os.path.exists(news_file):
        print("news.json not found")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news = json.load(f)

    unique_news = []
    
    # Procesamos en orden cronológico (las más antiguas primero, o mantener el orden del feed)
    # y cuando encontramos un duplicado, decidimos cuál mantener basándonos en la calidad.
    for item in news:
        if item.get('is_summary'):
            unique_news.append(item)
            continue
            
        duplicate_index = -1
        for i, existing in enumerate(unique_news):
            if not existing.get('is_summary') and are_duplicates(item, existing):
                duplicate_index = i
                break
                
        if duplicate_index == -1:
            unique_news.append(item)
        else:
            existing_item = unique_news[duplicate_index]
            if is_better_version(item, existing_item):
                print(f"Reemplazando duplicado: '{existing_item.get('title')}' ({existing_item.get('source')}) -> '{item.get('title')}' ({item.get('source')})")
                unique_news[duplicate_index] = item
            else:
                print(f"Ignorando duplicado de menor calidad: '{item.get('title')}' ({item.get('source')})")

    with open(news_file, 'w', encoding='utf-8') as f:
        json.dump(unique_news, f, indent=2, ensure_ascii=False)
    
    print(f"Deduplicación completada. Antes: {len(news)}, Ahora: {len(unique_news)}")

if __name__ == "__main__":
    deduplicate_news()

