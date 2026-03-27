import os
import requests
import json
import time
import hashlib
from bs4 import BeautifulSoup
from analyze_sentiment import analyze_sentiment, translate_to_euskara, translate_to_polish, rewrite_article

# Re-importing clean_body logic to be standalone
import re

def clean_body(p_tags):
    blacklist = ["©", "todos los derechos reservados", "fotografía:", "cedida", "| actualizado", "primer periódico digital de vitoria", "noticias vitoria-álava"]
    valid_paragraphs = []
    for p in p_tags:
        text = " ".join(p.get_text().split()).strip()
        text = re.sub(r'^\d{2}·\d{2}·\d{2}\s*\|\s*\d{2}:\d{2}(\s*\|\s*Actualizado.*?)?', '', text).strip()
        if len(text) < 40 or any(b in text.lower() for b in blacklist):
            continue
        valid_paragraphs.append(text)
    return "\n".join(valid_paragraphs)

def extract_original_content(url, source):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        title = ""
        body = ""
        
        if "elcorreo.com" in url:
            script_tag = soup.find('script', type='application/ld+json')
            if script_tag:
                ld = json.loads(script_tag.string)
                if isinstance(ld, list): ld = ld[0]
                if "@graph" in ld:
                    articles = [item for item in ld["@graph"] if item.get("@type") in ["NewsArticle", "Article"]]
                    if articles: ld = articles[0]
                title = ld.get('headline', '')
            p_tags = soup.select('div.v-p-b p, article p')
            body = clean_body(p_tags)
            
        elif "gasteizhoy.com" in url:
            h1 = soup.find('h1')
            title = h1.get_text().strip() if h1 else ""
            p_tags = soup.select('div.entry-content p, article p, div.contenido p, main p')
            body = clean_body(p_tags)
            
        elif "noticiasdealava.eus" in url:
            h1 = soup.find('h1')
            title = h1.get_text().strip() if h1 else ""
            p_tags = soup.select('div.v-p-b p, article p, div.contenido p, main p')
            body = clean_body(p_tags)
            
        return title, body
    except Exception as e:
        print(f"Error extrayendo {url}: {e}")
        return None, None

def main():
    news_file = 'data/news.json'
    if not os.path.exists(news_file):
        print("No hay news.json")
        return
        
    with open(news_file, 'r', encoding='utf-8') as f:
        news = json.load(f)
        
    print(f"Iniciando reprocesamiento de {len(news)} noticias...")
    
    for i, item in enumerate(news):
        url = item.get('url')
        if not url: continue
        
        # SALTAR SI YA ESTÁ PROCESADO (Body largo + ambas traducciones)
        if len(item.get('body', '')) > 800 and item.get('body_eu') and item.get('body_pl'):
            print(f"[{i+1}/{len(news)}] Saltando (ya detallado): {url}")
            continue

        print(f"[{i+1}/{len(news)}] Reprocesando: {url}")
        
        # 1. Recuperar original
        orig_title, orig_body = extract_original_content(url, item['source'])
        if not orig_title or not orig_body:
            print(f"  ! No se pudo recuperar contenido original para {url}. Saltando.")
            # Si no podemos recuperar el original, al menos intentamos traducir lo que hay si falta
            orig_title = item.get('title')
            orig_body = item.get('body')
            if not orig_title or not orig_body: continue
            
        # 2. Análisis (opcional actualizar sentimiento/categoría)
        sentiment, score, category = analyze_sentiment(orig_title + " " + orig_body[:500])
        
        # 3. Reescribir (NUEVO MODELO DETALLADO)
        # Solo reescribir si el cuerpo actual es corto
        if len(item.get('body', '')) < 800:
            new_title_rw, new_body_rw = rewrite_article(orig_title, orig_body)
            if new_title_rw and new_body_rw:
                item['title'] = new_title_rw
                item['body'] = new_body_rw
                print("  ✓ Título y cuerpo reescritos con detalle.")
            else:
                print("  ! Fallo en reescritura.")
            
        # 4. Traducciones (Asegurar que están completas)
        if not item.get('body_eu'):
            time.sleep(2)
            title_eu, body_eu = translate_to_euskara(orig_title, orig_body)
            if title_eu: 
                item['title_eu'] = title_eu
                item['body_eu'] = body_eu
                print("  ✓ Traducción Euskara actualizada.")
            else:
                print("  ! Fallo en traducción Euskara.")
            
        if not item.get('body_pl'):
            time.sleep(2)
            title_pl, body_pl = translate_to_polish(orig_title, orig_body)
            if title_pl:
                item['title_pl'] = title_pl
                item['body_pl'] = body_pl
                print("  ✓ Traducción Polaco actualizada.")
            else:
                print("  ! Fallo en traducción Polaco.")
            
        # Guardar cada 2 para no perder progreso (70b es más caro/lento)
        if (i + 1) % 2 == 0:
            with open(news_file, 'w', encoding='utf-8') as f:
                json.dump(news, f, indent=2, ensure_ascii=False)
            print(f"--- Progreso guardado ({i+1}) ---")
            
        time.sleep(1) # Cooldown general para evitar TPM

    # Guardado final
    with open(news_file, 'w', encoding='utf-8') as f:
        json.dump(news, f, indent=2, ensure_ascii=False)
    print("Reprocesamiento completado con éxito.")

if __name__ == "__main__":
    main()
