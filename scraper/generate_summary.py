import json
import os
import random
import time
from datetime import datetime, date
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

def get_groq_client():
    """Get a Groq client using the dedicated GROQ_RESUMEN API key."""
    api_key = os.environ.get("GROQ_RESUMEN")
    if not api_key:
        print("ERROR: No se encontró la variable de entorno GROQ_RESUMEN")
        return None
    return Groq(api_key=api_key)

def _title_words(title):
    """Return a set of significant lowercase words from a title (≥4 chars)."""
    return {w.lower() for w in title.split() if len(w) >= 4}

def _similarity(t1, t2):
    """Jaccard similarity between two title word sets."""
    a, b = _title_words(t1), _title_words(t2)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

def deduplicate_news(items, preferred_source="El Correo", threshold=0.4):
    """
    Remove duplicate stories about the same topic.
    When duplicates exist, keep the one from preferred_source; otherwise keep the first seen.
    """
    kept = []
    for item in items:
        title = item.get('title', '')
        duplicate = False
        for i, kept_item in enumerate(kept):
            if _similarity(title, kept_item.get('title', '')) >= threshold:
                # Same story — prefer El Correo
                if item.get('source', '') == preferred_source and kept_item.get('source', '') != preferred_source:
                    kept[i] = item  # swap
                duplicate = True
                break
        if not duplicate:
            kept.append(item)
    return kept

def get_today_news(news_data):
    """Filter today-only news from Alava/Deportes, deduplicated preferring El Correo."""
    today = date.today()
    today_items = []
    for item in news_data:
        if item.get('is_summary'):
            continue
        try:
            item_date = datetime.fromisoformat(item.get('date', '')).date()
            # Only today's news (not yesterday)
            if item_date == today:
                section = str(item.get('category') or item.get('source_section', '')).strip().lower()
                if 'alava' in section or 'álava' in section or 'deportes' in section:
                    today_items.append(item)
        except (ValueError, TypeError):
            continue

    before = len(today_items)
    today_items = deduplicate_news(today_items)
    print(f"  Noticias tras deduplicar: {len(today_items)} (de {before} originales)")
    return today_items

def format_news_item(item, preview_chars=300):
    """Format a single news item as a text line for the prompt."""
    title = item.get('title', '')
    source = item.get('source', '')
    section = item.get('category') or item.get('source_section', '')
    body_preview = item.get('body', '')[:preview_chars]
    return f"- [{source}] ({section}) {title}\n  {body_preview}"

def summarize_chunk(client, chunk_items, chunk_num, total_chunks):
    """Ask Groq to extract key bullet points from a chunk of news items."""
    news_text = "\n\n".join(format_news_item(item) for item in chunk_items)

    system_prompt = (
        "Eres un redactor de noticias. Tu tarea es extraer los PUNTOS CLAVE "
        "de una lista de noticias de Álava y deportes. "
        "Devuelve una lista de 5 a 10 puntos clave en español, uno por línea, "
        "comenzando cada uno con '- '. Sin títulos, sin JSON, solo los puntos."
    )
    user_prompt = (
        f"Estas son las noticias del bloque {chunk_num}/{total_chunks}. "
        f"Extrae los hechos más relevantes:\n\n{news_text}"
    )

    print(f"  Procesando chunk {chunk_num}/{total_chunks} ({len(chunk_items)} noticias)...")
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=512,
    )
    return completion.choices[0].message.content.strip()

def synthesize_summaries(client, bullet_summaries, total_news):
    """Combine all bullet-point chunks into a single narrative daily summary."""
    combined = "\n\n".join(
        f"=== Bloque {i+1} ===\n{s}" for i, s in enumerate(bullet_summaries)
    )

    system_prompt = """Eres un periodista experto y analista de la actualidad de Vitoria-Gasteiz y Álava.
Tu tarea es generar un RESUMEN DIARIO de las noticias más importantes del día a partir de un conjunto de puntos clave.

El resumen debe:
1. Tener un TÍTULO atractivo y periodístico que refleje el tema principal del día (máximo 10 palabras)
2. Un BREVE LEAD de apertura (1-2 frases) que contextualice la jornada informativa
3. Un DESARROLLO organizado por temas (Álava y Deportes), conectando las noticias relacionadas entre sí
4. Una FRASE DE CIERRE que deje una reflexión o mirada al día siguiente
5. Estilo narrativo fluido, como un boletín informativo de radio o un editorial breve
6. Extensión total: entre 300 y 600 palabras

Formato de respuesta JSON:
{
  "title": "Título atractivo del resumen",
  "summary": "Texto completo del resumen con lead, desarrollo y cierre"
}

No incluyas firmas, ni menciones a Gasteiz Live. Limítate al resumen periodístico."""

    user_prompt = (
        f"A continuación tienes los puntos clave extraídos de {total_news} noticias de hoy "
        f"en Vitoria-Gasteiz (Álava y Deportes). Genera un resumen diario cohesivo:\n\n{combined}"
    )

    print("  Generando resumen final...")
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.5,
        response_format={"type": "json_object"},
        max_tokens=1024,
    )
    result = json.loads(completion.choices[0].message.content)
    return result.get('title', 'Resumen del día'), result.get('summary', '')

def generate_daily_summary(news_items):
    """Use Groq with chunking to generate a comprehensive daily news summary."""
    if not news_items:
        print("No hay noticias del día para resumir.")
        return None

    client = get_groq_client()
    if not client:
        print("No hay API keys de Groq disponibles.")
        return None

    CHUNK_SIZE = 20          # ~20 noticias por llamada → ~8k tokens de entrada
    SLEEP_BETWEEN_CHUNKS = 62  # segundos para resetear la ventana TPM de Groq

    # Dividir en chunks
    chunks = [news_items[i:i + CHUNK_SIZE] for i in range(0, len(news_items), CHUNK_SIZE)]
    total_chunks = len(chunks)
    print(f"Generando resumen diario con Groq: {len(news_items)} noticias en {total_chunks} chunks...")

    bullet_summaries = []
    for idx, chunk in enumerate(chunks, start=1):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                bullet = summarize_chunk(client, chunk, idx, total_chunks)
                bullet_summaries.append(bullet)
                break
            except Exception as e:
                print(f"  Error en chunk {idx} (intento {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)
        else:
            print(f"  ⚠️  No se pudo procesar el chunk {idx}, se omite.")

        # Sleep between chunks (except after the last one)
        if idx < total_chunks:
            print(f"  Esperando {SLEEP_BETWEEN_CHUNKS}s para respetar el límite de Groq...")
            time.sleep(SLEEP_BETWEEN_CHUNKS)

    if not bullet_summaries:
        print("No se pudieron obtener resúmenes de ningún chunk.")
        return None

    # Final synthesis call (also with retry)
    # Wait before the synthesis call if we processed more than one chunk
    if total_chunks > 1:
        print(f"  Esperando {SLEEP_BETWEEN_CHUNKS}s antes de la síntesis final...")
        time.sleep(SLEEP_BETWEEN_CHUNKS)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            title, summary = synthesize_summaries(client, bullet_summaries, len(news_items))
            if summary:
                print(f"Resumen generado: {title}")
                return {'title': title, 'body': summary}
        except Exception as e:
            print(f"Error generando síntesis (intento {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5)

    return None


def add_summary_to_news(news_data, summary_data):
    """Add the summary as a special entry in the news data."""
    if not summary_data:
        return news_data
    
    today_str = datetime.now().isoformat()
    
    # Remove any existing summary for today
    news_data = [item for item in news_data if not item.get('is_summary')]
    
    summary_entry = {
        'id': f'resumen_{date.today().isoformat()}',
        'title': summary_data['title'],
        'body': summary_data['body'],
        'url': '',
        'source': 'Gasteiz Live',
        'date': today_str,
        'sentiment': 0.2,
        'image': '',
        'source_section': 'resumen',
        'category': 'Resumen del Día',
        'is_summary': True,
        'rewritten': False
    }
    
    # Insert summary at the beginning
    news_data.insert(0, summary_entry)
    print(f"Resumen diario añadido al inicio de news.json")
    return news_data

def main():
    news_file = 'data/news.json'
    if not os.path.exists(news_file):
        print(f"No se encontró {news_file}")
        return
    
    with open(news_file, 'r', encoding='utf-8') as f:
        news_data = json.load(f)
    
    today_news = get_today_news(news_data)
    print(f"Noticias de hoy encontradas: {len(today_news)}")
    
    if len(today_news) < 2:
        print("No hay suficientes noticias del día para generar un resumen (mínimo 2).")
        return
    
    summary_data = generate_daily_summary(today_news)
    if not summary_data:
        print("No se pudo generar el resumen.")
        return
    
    news_data = add_summary_to_news(news_data, summary_data)
    
    with open(news_file, 'w', encoding='utf-8') as f:
        json.dump(news_data, f, indent=2, ensure_ascii=False)
    
    print("Resumen diario generado y guardado correctamente.")

if __name__ == "__main__":
    main()