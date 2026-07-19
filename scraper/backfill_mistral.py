"""
Backfill de las ultimas 10 noticias con la nueva funcionalidad de Mistral.
Verifica y corrige las traducciones existentes (eu, pl, fr, en) comparandolas con el original en español.
Ejecutar manualmente: python scraper/backfill_mistral.py
"""
import json
import os
import sys
import time

# Para poder importar desde la carpeta scraper
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from analyze_sentiment import verify_translation_with_mistral, replace_vitoria_basque

def backfill_mistral():
    # Ruta al archivo de noticias (relativa a la raíz del proyecto)
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root_dir)
    news_file = 'data/news.json'

    if not os.path.exists(news_file):
        print(f"No se encontro {news_file}")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news = json.load(f)

    # Seleccionar las primeras 10 noticias (las mas recientes)
    target_news = news[:10]
    print(f"Iniciando backfill de las {len(target_news)} noticias mas recientes con Mistral...\n")

    changes = []
    langs = ['eu', 'pl', 'fr', 'en']

    for i, item in enumerate(target_news, start=1):
        url = item.get('url') or f"Resumen ID: {item.get('id')}"
        title_es = item.get('title', '')
        body_es = item.get('body', '')

        print(f"\n[{i}/{len(target_news)}] Procesando noticia: {url}")

        if not title_es or not body_es:
            print("  [SALTADA] Sin titulo o cuerpo en espanol.")
            continue

        for lang in langs:
            # Claves de traduccion en el JSON
            title_key = f"title_{lang}"
            body_key = f"body_{lang}"
            translated_flag = f"translated_{lang}"

            # Verificar si existe la traduccion para procesar
            if item.get(translated_flag) or item.get(title_key) or item.get(body_key):
                orig_title_tr = item.get(title_key, '')
                orig_body_tr = item.get(body_key, '')

                print(f"  - Verificando idioma: {lang.upper()}")

                # 1. Verificar titulo
                if orig_title_tr:
                    verified_title = verify_translation_with_mistral(title_es, orig_title_tr, lang, 'TÍTULO')
                    if lang == "eu" and verified_title:
                        verified_title = replace_vitoria_basque(verified_title)
                    
                    if verified_title and verified_title != orig_title_tr:
                        changes.append({
                            'url': url,
                            'title': title_es,
                            'lang': lang.upper(),
                            'field': 'TÍTULO',
                            'before': orig_title_tr,
                            'after': verified_title
                        })
                        item[title_key] = verified_title
                        print(f"    [CAMBIO] Titulo corregido.")

                # 2. Verificar cuerpo (por párrafos o completo, usaremos completo)
                # Para el cuerpo, como en analyze_sentiment lo dividimos en fragmentos grandes,
                # aqui podemos pasarlo completo o fragmento a fragmento. 
                # Si el cuerpo es muy largo, lo dividimos en fragmentos para evitar limites de contexto de Mistral.
                if orig_body_tr:
                    # Dividir en parrafos similares a translate_article
                    paragraphs = orig_body_tr.split('\n\n')
                    paragraphs_es = body_es.split('\n\n')
                    
                    # Para mantener simpleza, si coinciden en numero de parrafos, verificamos parrafo por parrafo.
                    # De lo contrario, lo verificamos en fragmentos de hasta 2500 caracteres.
                    verified_paragraphs = []
                    has_body_change = False

                    if len(paragraphs) == len(paragraphs_es):
                        # Verificacion parrafo por parrafo
                        for idx, (p_es, p_tr) in enumerate(zip(paragraphs_es, paragraphs)):
                            if not p_tr.strip():
                                verified_paragraphs.append("")
                                continue
                            
                            v_p = verify_translation_with_mistral(p_es, p_tr, lang, 'CUERPO')
                            if lang == "eu" and v_p:
                                v_p = replace_vitoria_basque(v_p)
                            
                            if v_p and v_p != p_tr:
                                has_body_change = True
                                changes.append({
                                    'url': url,
                                    'title': title_es,
                                    'lang': lang.upper(),
                                    'field': f'CUERPO (Párrafo {idx+1})',
                                    'before': p_tr,
                                    'after': v_p
                                })
                            verified_paragraphs.append(v_p or p_tr)
                            time.sleep(0.5)
                    else:
                        # Verificacion en bloques de texto completo si no coinciden parrafos
                        chunks_es = []
                        current_chunk = []
                        current_len = 0
                        for p in paragraphs_es:
                            if current_len + len(p) > 2500 and current_chunk:
                                chunks_es.append("\n\n".join(current_chunk))
                                current_chunk = [p]
                                current_len = len(p)
                            else:
                                current_chunk.append(p)
                                current_len += len(p) + 2
                        if current_chunk:
                            chunks_es.append("\n\n".join(current_chunk))

                        chunks_tr = []
                        current_chunk = []
                        current_len = 0
                        for p in paragraphs:
                            if current_len + len(p) > 2500 and current_chunk:
                                chunks_tr.append("\n\n".join(current_chunk))
                                current_chunk = [p]
                                current_len = len(p)
                            else:
                                current_chunk.append(p)
                                current_len += len(p) + 2
                        if current_chunk:
                            chunks_tr.append("\n\n".join(current_chunk))

                        for idx, (c_es, c_tr) in enumerate(zip(chunks_es, chunks_tr)):
                            v_c = verify_translation_with_mistral(c_es, c_tr, lang, 'CUERPO')
                            if lang == "eu" and v_c:
                                v_c = replace_vitoria_basque(v_c)
                            
                            if v_c and v_c != c_tr:
                                has_body_change = True
                                changes.append({
                                    'url': url,
                                    'title': title_es,
                                    'lang': lang.upper(),
                                    'field': f'CUERPO (Bloque {idx+1})',
                                    'before': c_tr,
                                    'after': v_c
                                })
                            verified_paragraphs.append(v_c or c_tr)
                            time.sleep(0.5)

                    if has_body_change:
                        item[body_key] = "\n\n".join(verified_paragraphs)
                        print(f"    [CAMBIO] Cuerpo corregido.")

                # Breve espera para rate limits de Mistral entre idiomas
                time.sleep(1.0)

    # Guardar las noticias actualizadas
    with open(news_file, 'w', encoding='utf-8') as f:
        json.dump(news, f, indent=2, ensure_ascii=False)

    print("\n--- Backfill Finalizado ---")
    print(f"Total de correcciones realizadas por Mistral: {len(changes)}")

    # Generar el informe en markdown
    generate_markdown_report(changes)

def generate_markdown_report(changes):
    report_path = r"C:\Users\ortas\.gemini\antigravity-ide\brain\829c3160-a25e-4a52-81ae-764bc7020f02\mistral_backfill_report.md"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Informe de Verificación y Correcciones de Mistral\n\n")
        f.write(f"Se ha analizado el histórico de las últimas **10 noticias** en `data/news.json` y se han verificado sus traducciones (euskera, polaco, francés, inglés) con Mistral.\n\n")
        f.write(f"**Total de correcciones de estilo/gramática aplicadas:** {len(changes)}\n\n")
        
        if not changes:
            f.write("## 🎉 ¡No se detectaron errores!\n")
            f.write("Mistral consideró que todas las traducciones analizadas eran correctas, fluidas y precisas. No se realizaron cambios.\n")
            return

        f.write("## Detalle de Correcciones\n\n")
        for idx, change in enumerate(changes, 1):
            f.write(f"### {idx}. [{change['lang']}] {change['field']}\n")
            f.write(f"- **Noticia original**: {change['title']}\n")
            f.write(f"- **Enlace/ID**: {change['url']}\n\n")
            
            f.write("```diff\n")
            # Mostrar diferencias línea por línea de forma simplificada
            f.write(f"- {change['before']}\n")
            f.write(f"+ {change['after']}\n")
            f.write("```\n\n")
            f.write("---\n\n")

    print(f"Informe completo guardado en: {report_path}")

if __name__ == "__main__":
    backfill_mistral()
