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

def get_today_news(news_data):
    """Filter news items from today and yesterday."""
    today = date.today()
    today_items = []
    for item in news_data:
        try:
            item_date = datetime.fromisoformat(item.get('date', '')).date()
            # Include today and yesterday's news
            if (today - item_date).days <= 1:
                today_items.append(item)
        except (ValueError, TypeError):
            continue
    return today_items

def generate_daily_summary(news_items):
    """Use Groq to generate a comprehensive daily news summary."""
    if not news_items:
        print("No hay noticias del día para resumir.")
        return None

    # Prepare a concise list of today's news for the prompt (limit to top 50 items to avoid token limits)
    news_list = []
    for item in news_items[:50]:
        title = item.get('title', '')
        source = item.get('source', '')
        section = item.get('category') or item.get('source_section', '')
        body_preview = item.get('body', '')[:150]  # Reduce preview to 150 chars
        news_list.append(f"- [{source}] ({section}) {title}\n  {body_preview}")

    news_text = "\n\n".join(news_list)
    
    # Truncate to ensure it doesn't exceed roughly 8000 tokens (~32000 chars)
    if len(news_text) > 30000:
        news_text = news_text[:30000] + "\n...[Truncated]"
    
    print(f"Generando resumen diario con Groq para {len(news_items)} noticias...")

    client = get_groq_client()
    if not client:
        print("No hay API keys de Groq disponibles.")
        return None

    system_prompt = """Eres un periodista experto y analista de la actualidad de Vitoria-Gasteiz y Álava.
Tu tarea es generar un RESUMEN DIARIO de las noticias más importantes del día.

El resumen debe:
1. Tener un TÍTULO atractivo y periodístico que refleje el tema principal del día (máximo 10 palabras)
2. Un BREVE LEAD de apertura (1-2 frases) que contextualice la jornada informativa
3. Un DESARROLLO organizado por temas, conectando las noticias relacionadas entre sí
4. Una FRASE DE CIERRE que deje una reflexión o mirada al día siguiente
5. Estilo narrativo fluido, como un boletín informativo de radio o un editorial breve
6. Extensión total: entre 300 y 600 palabras

Formato de respuesta JSON:
{
  "title": "Título atractivo del resumen",
  "summary": "Texto completo del resumen con lead, desarrollo y cierre"
}

No incluyas firmas, ni menciones a Gasteiz Live. Limítate al resumen periodístico."""

    user_prompt = f"Estas son las noticias de hoy en Vitoria-Gasteiz. Genera un resumen diario cohesivo y bien estructurado:\n\n{news_text}"

    max_retries = 3
    for attempt in range(max_retries):
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5,
                response_format={"type": "json_object"}
            )
            result = json.loads(completion.choices[0].message.content)
            title = result.get('title', 'Resumen del día')
            summary = result.get('summary', '')
            
            if summary:
                print(f"Resumen generado: {title}")
                return {
                    'title': title,
                    'body': summary
                }
        except Exception as e:
            print(f"Error generando resumen (intento {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
    
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