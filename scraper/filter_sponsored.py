import os
import json
import time
import random
import re
from groq import Groq
from dotenv import load_dotenv
from key_rotator import get_next_key

# Cargar variables de entorno
load_dotenv()

def clean_thinking_tags(text):
    """Elimina bloques <think>...</think> que genera Qwen en modo thinking."""
    if not text:
        return text
    return re.sub(r'<think>[\s\S]*?(?:</think>|$)', '', text).strip()

def get_groq_client():
    """Obtiene el cliente Groq priorizando DEDUPLICITY2, luego DEDUPLICITY1 y otras fallbacks."""
    keys = [
        os.environ.get("DEDUPLICITY2"),
        os.environ.get("DEDUPLICITY1"),
    ]
    # Añadir llaves genéricas extras
    for i in range(1, 11):
        extra_key = os.environ.get(f"GROQ_EXTRA{i}")
        if extra_key:
            keys.append(extra_key)
            
    valid_keys = [k for k in keys if k]
    if not valid_keys:
        return None
    api_key = get_next_key(valid_keys, "sponsored")
    return Groq(api_key=api_key)

def check_sponsored_llm(title, body):
    """Envía la noticia a Qwen para determinar si es un publirreportaje o patrocinio encubierto."""
    client = get_groq_client()
    if not client:
        print("    [AVISO] No hay claves de Groq disponibles. Se saltará la detección de patrocinados.")
        return False, "No key available"

    content = f"Título: {title}\n\nCuerpo:\n{body[:1500]}"

    system_prompt = """Eres un periodista de investigación y director editorial sumamente crítico. Tu tarea es analizar una noticia local de Vitoria-Gasteiz y determinar si se trata de un "publirreportaje encubierto" o "noticia patrocinada encubierta" (advertorial).

CRITERIOS PARA DETECTAR CONTENIDO PATROCINADO ENCUBIERTO:
1. El artículo está redactado de forma laudatoria o promocional sobre una empresa privada, negocio local, marca, producto, servicio, clínica, profesional, academia, hotel o restaurante.
2. La noticia se centra en la apertura, lanzamiento, historia de éxito, servicios, tarifas o bondades de una entidad comercial sin un valor informativo o de interés público real para la ciudadanía general.
3. Incluye información de contacto directo de la empresa (dirección, web, teléfono, redes sociales) de forma poco orgánica o enlaces de compra/reserva.
4. El tono es publicitario o comercial ("la mejor opción", "soluciones a tu medida", "expertos en su sector").
5. Artículos sobre análisis de ADN comerciales, seguros, clínicas estéticas, ópticas locales, etc., suelen ser patrocinios de este tipo.

Responde estrictamente en formato JSON con el siguiente esquema exacto:
{
  "is_sponsored": true / false,
  "reason": "Explicación breve de por qué se considera patrocinado o no"
}
No devuelvas ninguna otra explicación, ni bloques de código markdown, solo el JSON puro."""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            completion = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}
                ],
                temperature=0.0,
                response_format={"type": "json_object"},
                extra_body={"reasoning_effort": "none"}
            )
            
            response_text = completion.choices[0].message.content
            
            # Limpiar bloques de razonamiento <think>...</think> de Qwen
            clean_text = clean_thinking_tags(response_text)
            # Limpiar posibles bloques markdown
            if clean_text.startswith("```"):
                clean_text = re.sub(r"^```[a-zA-Z]*\n", "", clean_text)
                clean_text = re.sub(r"\n```$", "", clean_text)
                clean_text = clean_text.strip()
                
            data = json.loads(clean_text)
            return data.get("is_sponsored", False), data.get("reason", "")
        except Exception as e:
            print(f"    [AVISO] Intento {attempt + 1} de detección de patrocinado falló: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
    return False, "Error in LLM"

def filter_sponsored_news():
    """Analiza y descarta las noticias patrocinadas encubiertas de Gasteiz Hoy."""
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    news_file = os.path.join(root_dir, 'data', 'news.json')
    
    if not os.path.exists(news_file):
        print(f"Error: No se encontró el archivo de noticias: {news_file}")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news_items = json.load(f)

    # Filtrar resúmenes
    regular_items = [item for item in news_items if not item.get('is_summary')]
    summary_items = [item for item in news_items if item.get('is_summary')]

    final_regular = []
    skipped_count = 0
    filtered_count = 0

    print("Iniciando escaneo de noticias patrocinadas encubiertas de Gasteiz Hoy...")
    
    for item in regular_items:
        # Solo comprobar noticias de Gasteiz Hoy
        is_gasteiz_hoy = item.get('source') == 'Gasteiz Hoy'
        is_checked = item.get('sponsored_checked') == True

        if not is_gasteiz_hoy:
            final_regular.append(item)
            continue

        if is_checked:
            final_regular.append(item)
            skipped_count += 1
            continue

        # Llamar al LLM para comprobar patrocinio
        title = item.get('original_title') or item.get('title', '')
        body = item.get('original_body') or item.get('body', '')
        url = item.get('url', '')
        
        print(f"  [LLM] Evaluando patrocinio para: '{title}' ({url})")
        is_sponsored, reason = check_sponsored_llm(title, body)
        
        if is_sponsored:
            print(f"  [FILTRADO] Omitiendo post patrocinado: '{title}'")
            print(f"             Razón: {reason}")
            filtered_count += 1
            # Omitimos añadirlo a final_regular
        else:
            print(f"  [CONSERVADO] Artículo legítimo verificado: '{title}'")
            item['sponsored_checked'] = True
            final_regular.append(item)
            
        time.sleep(0.5)

    # Unir con resúmenes del día
    final_news = summary_items + final_regular

    # Guardar en news.json
    with open(news_file, 'w', encoding='utf-8') as f:
        json.dump(final_news, f, indent=2, ensure_ascii=False)
        
    print(f"\nEscaneo de patrocinios completado. Conservadas en cache: {skipped_count}, Filtradas: {filtered_count}")

if __name__ == "__main__":
    filter_sponsored_news()
