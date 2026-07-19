import json
import os
import random
import time
from datetime import datetime, date
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

def clean_thinking_tags(text):
    """Elimina bloques <think>...</think> que genera Qwen en modo thinking."""
    if not text:
        return text
    return re.sub(r'<think>[\s\S]*?(?:</think>|$)', '', text).strip()

def get_groq_client():
    """Get a Groq client using the dedicated GROQ_RESUMEN API key, with generic backups."""
    keys = [os.environ.get("GROQ_RESUMEN")]
    # Añadir llaves genéricas extras como backup
    for i in range(1, 11):
        extra_key = os.environ.get(f"GROQ_EXTRA{i}")
        if extra_key:
            keys.append(extra_key)
            
    valid_keys = [k for k in keys if k]
    if not valid_keys:
        print("ERROR: No se encontraron variables de entorno de Groq válidas")
        return None
        
    # Priorizar la clave oficial
    api_key = os.environ.get("GROQ_RESUMEN") or random.choice(valid_keys)
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

def get_existing_summary(news_data):
    """Find the existing summary entry for today, if any."""
    today_str = date.today().isoformat()
    for item in news_data:
        if item.get('is_summary'):
            # Check if it's today's summary by ID prefix or date
            item_id = item.get('id', '')
            if item_id == f'resumen_{today_str}' or item.get('source_section') == 'resumen':
                # Also verify it was created today
                try:
                    item_date = datetime.fromisoformat(item.get('date', '')).date()
                    if item_date == date.today():
                        return item
                except:
                    pass
    return None

def get_unsummarized_news(all_news, summarized_ids):
    """Get today's news that have NOT been summarized yet."""
    today = date.today()
    new_items = []
    for item in all_news:
        if item.get('is_summary'):
            continue
        try:
            item_date = datetime.fromisoformat(item.get('date', '')).date()
            if item_date != today:
                continue
        except (ValueError, TypeError):
            continue

        news_id = item.get('id')
        if news_id and news_id in summarized_ids:
            continue

        section = str(item.get('category') or item.get('source_section', '')).strip().lower()
        if 'alava' in section or 'álava' in section or 'deportes' in section:
            new_items.append(item)

    before = len(new_items)
    new_items = deduplicate_news(new_items)
    print(f"  Noticias nuevas NO resumidas: {len(new_items)} (de {before} originales)")
    return new_items

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
        model="qwen/qwen3.6-27b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=512,
        extra_body={"reasoning_effort": "none"}
    )
    return clean_thinking_tags(completion.choices[0].message.content)

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
        model="qwen/qwen3.6-27b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.5,
        response_format={"type": "json_object"},
        max_tokens=1024,
        extra_body={"reasoning_effort": "none"}
    )
    raw_response = clean_thinking_tags(completion.choices[0].message.content)
    result = json.loads(raw_response)
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
    SLEEP_BETWEEN_CHUNKS = 12  # segundos de cortesía; si hay rate limit, el retry lo gestiona

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

def expand_existing_summary(client, existing_summary, new_bullet_points):
    """Merge existing summary with new bullet points into an expanded narrative."""
    system_prompt = """Eres un periodista experto y analista de la actualidad de Vitoria-Gasteiz y Álava.
Tu tarea es AMPLIAR un resumen diario existente añadiendo nuevas noticias que han ocurrido a lo largo del día.

Tienes:
1. El resumen actual (que cubre noticias anteriores del día)
2. Nuevos puntos clave de noticias más recientes

Debes generar un resumen diario ACTUALIZADO que integre TODO (lo anterior + lo nuevo) en un único texto fluido.

El resumen debe:
1. Mantener el TÍTULO actual si sigue siendo representativo, o actualizarlo ligeramente si las nuevas noticias cambian el tema principal
2. Un LEAD de apertura actualizado que refleje el conjunto completo de la jornada
3. Un DESARROLLO que integre las noticias nuevas con las ya existentes, organizado por temas
4. Una FRASE DE CIERRE actualizada
5. Estilo narrativo fluido, como un boletín informativo de radio
6. Extensión total: entre 300 y 800 palabras (puede crecer respecto al resumen anterior)

Formato de respuesta JSON:
{
  "title": "Título actualizado del resumen",
  "summary": "Texto completo del resumen ampliado con lead, desarrollo y cierre"
}

No incluyas firmas, ni menciones a Gasteiz Live. Limítate al resumen periodístico."""

    user_prompt = (
        f"=== RESUMEN ACTUAL ===\n\n{existing_summary}\n\n"
        f"=== NUEVAS NOTICIAS (puntos clave) ===\n\n{new_bullet_points}\n\n"
        f"Amplía el resumen actual integrando estas nuevas noticias de forma natural."
    )

    print("  Ampliando resumen existente con nuevas noticias...")
    completion = client.chat.completions.create(
        model="qwen/qwen3.6-27b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.5,
        response_format={"type": "json_object"},
        max_tokens=1500,
        extra_body={"reasoning_effort": "none"}
    )
    raw_response = clean_thinking_tags(completion.choices[0].message.content)
    result = json.loads(raw_response)
    return result.get('title', 'Resumen del día'), result.get('summary', '')

def incremental_summary(client, existing_summary, new_news_items):
    """Process new news items into bullet points, then merge into existing summary."""
    if not new_news_items:
        return existing_summary.get('title'), existing_summary.get('body')

    CHUNK_SIZE = 20
    SLEEP_BETWEEN_CHUNKS = 12

    # Divide new items into chunks and summarize them to bullet points
    chunks = [new_news_items[i:i + CHUNK_SIZE] for i in range(0, len(new_news_items), CHUNK_SIZE)]
    total_chunks = len(chunks)
    print(f"Resumiendo {len(new_news_items)} noticias nuevas en {total_chunks} chunks...")

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

        if idx < total_chunks:
            print(f"  Esperando {SLEEP_BETWEEN_CHUNKS}s...")
            time.sleep(SLEEP_BETWEEN_CHUNKS)

    if not bullet_summaries:
        print("No se pudieron obtener resúmenes de las nuevas noticias.")
        return existing_summary.get('title'), existing_summary.get('body')

    combined_new = "\n\n".join(
        f"=== Bloque {i+1} ===\n{s}" for i, s in enumerate(bullet_summaries)
    )

    if total_chunks > 1:
        print(f"  Esperando {SLEEP_BETWEEN_CHUNKS}s antes de la expansión...")
        time.sleep(SLEEP_BETWEEN_CHUNKS)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            new_title, new_body = expand_existing_summary(
                client,
                existing_summary.get('body', ''),
                combined_new
            )
            if new_body:
                print(f"Resumen ampliado: {new_title}")
                return new_title, new_body
        except Exception as e:
            print(f"Error ampliando resumen (intento {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5)

    # Fallback: return existing summary unchanged
    return existing_summary.get('title'), existing_summary.get('body')


def add_summary_to_news(news_data, summary_data):
    """Add or update the summary entry in the news data."""
    if not summary_data:
        return news_data
    
    today_str = datetime.now().isoformat()
    today_date_str = date.today().isoformat()
    
    # Remove any existing summary for today
    news_data = [item for item in news_data if not item.get('is_summary')]
    
    summary_entry = {
        'id': f'resumen_{today_date_str}',
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
        'rewritten': False,
        'summarized_news_ids': summary_data.get('summarized_news_ids', [])
    }
    
    # Traducir el resumen al euskera de forma inmediata
    try:
        from analyze_sentiment import translate_article
        print("Traduciendo resumen diario al euskera...", flush=True)
        title_eu, body_eu = translate_article(summary_data['title'], summary_data['body'], target_lang="eu")
        if title_eu and body_eu:
            summary_entry['title_eu'] = title_eu
            summary_entry['body_eu'] = body_eu
            summary_entry['translated_eu'] = True
            print("Resumen diario traducido al euskera con éxito.", flush=True)
        else:
            print("No se pudo obtener traducción del resumen al euskera.", flush=True)
    except Exception as e:
        print(f"Error al traducir el resumen diario al euskera: {e}", flush=True)

    # Traducir el resumen al polaco de forma inmediata
    try:
        from analyze_sentiment import translate_article
        print("Traduciendo resumen diario al polaco...", flush=True)
        title_pl, body_pl = translate_article(summary_data['title'], summary_data['body'], target_lang="pl")
        if title_pl and body_pl:
            summary_entry['title_pl'] = title_pl
            summary_entry['body_pl'] = body_pl
            summary_entry['translated_pl'] = True
            print("Resumen diario traducido al polaco con éxito.", flush=True)
        else:
            print("No se pudo obtener traducción del resumen al polaco.", flush=True)
    except Exception as e:
        print(f"Error al traducir el resumen diario al polaco: {e}", flush=True)

    # Traducir el resumen al francés de forma inmediata
    try:
        from analyze_sentiment import translate_article
        print("Traduciendo resumen diario al francés...", flush=True)
        title_fr, body_fr = translate_article(summary_data['title'], summary_data['body'], target_lang="fr")
        if title_fr and body_fr:
            summary_entry['title_fr'] = title_fr
            summary_entry['body_fr'] = body_fr
            summary_entry['translated_fr'] = True
            print("Resumen diario traducido al francés con éxito.", flush=True)
        else:
            print("No se pudo obtener traducción del resumen al francés.", flush=True)
    except Exception as e:
        print(f"Error al traducir el resumen diario al francés: {e}", flush=True)

    # Traducir el resumen al inglés de forma inmediata
    try:
        from analyze_sentiment import translate_article
        print("Traduciendo resumen diario al inglés...", flush=True)
        title_en, body_en = translate_article(summary_data['title'], summary_data['body'], target_lang="en")
        if title_en and body_en:
            summary_entry['title_en'] = title_en
            summary_entry['body_en'] = body_en
            summary_entry['translated_en'] = True
            print("Resumen diario traducido al inglés con éxito.", flush=True)
        else:
            print("No se pudo obtener traducción del resumen al inglés.", flush=True)
    except Exception as e:
        print(f"Error al traducir el resumen diario al inglés: {e}", flush=True)

    # Insert summary at the beginning
    news_data.insert(0, summary_entry)
    print(f"Resumen diario {'actualizado' if summary_data.get('is_update') else 'generado'} al inicio de news.json")
    return news_data


def main():
    news_file = 'data/news.json'
    if not os.path.exists(news_file):
        print(f"No se encontró {news_file}")
        return
    
    with open(news_file, 'r', encoding='utf-8') as f:
        news_data = json.load(f)
    
    # Check if there's already a summary for today
    existing_summary = get_existing_summary(news_data)
    
    if existing_summary:
        # --- Incremental mode: only summarize NEW news ---
        summarized_ids = set(existing_summary.get('summarized_news_ids', []))
        new_news = get_unsummarized_news(news_data, summarized_ids)
        
        if not new_news:
            print("No hay noticias nuevas desde el último resumen. No se actualiza.")
            return
        
        # Also include existing body for context in incremental update
        client = get_groq_client()
        if not client:
            print("No hay API keys de Groq disponibles.")
            return
        
        new_title, new_body = incremental_summary(client, existing_summary, new_news)
        
        # Collect all summarized IDs (previous + new)
        all_summarized_ids = summarized_ids | {item.get('id') for item in new_news if item.get('id')}
        
        summary_data = {
            'title': new_title,
            'body': new_body,
            'summarized_news_ids': list(all_summarized_ids),
            'is_update': True
        }
    else:
        # --- First time today: generate full summary ---
        today_news = get_today_news(news_data)
        print(f"Noticias de hoy encontradas: {len(today_news)}")
        
        if len(today_news) < 2:
            print("No hay suficientes noticias del día para generar un resumen (mínimo 2).")
            return
        
        summary_data = generate_daily_summary(today_news)
        if not summary_data:
            print("No se pudo generar el resumen.")
            return
        
        # Track which news IDs were summarized
        summarized_ids = [item.get('id') for item in today_news if item.get('id')]
        summary_data['summarized_news_ids'] = summarized_ids
        summary_data['is_update'] = False
    
    news_data = add_summary_to_news(news_data, summary_data)
    
    with open(news_file, 'w', encoding='utf-8') as f:
        json.dump(news_data, f, indent=2, ensure_ascii=False)
    
    print("Resumen diario generado y guardado correctamente.")


if __name__ == "__main__":
    main()