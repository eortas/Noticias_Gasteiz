import re
import os
import json
from groq import Groq

# Fallback basic dictionaries
PALABRAS_POSITIVAS = {
    'bueno', 'buena', 'mejor', 'excelente', 'positivo', 'éxito', 'logro', 'avanza', 'mejora', 
    'beneficio', 'alegría', 'feliz', 'oportunidad', 'crecimiento', 'esperanza', 'solución',
    'paz', 'seguro', 'impulsa', 'apoyo', 'vanguardia', 'moderno', 'eficiente', 'gratis',
    'estrena', 'inaugura', 'récord', 'lidera', 'brilla', 'talento', 'unión', 'solidario',
    'relevo', 'continuidad', 'tradición', 'familia', 'futuro', 'crean', 'vuelve', 'abre', 'abren'
}

PALABRAS_NEGATIVAS = {
    'malo', 'mala', 'peor', 'negativo', 'fracaso', 'error', 'problema', 'crisis', 'daño', 
    'muerte', 'fallece', 'accidente', 'robo', 'detenido', 'agresión', 'pelea', 'herido',
    'denuncia', 'corte', 'huelga', 'protesta', 'incendio', 'atropello', 'crimen', 'estafa',
    'pérdida', 'caída', 'baja', 'tensión', 'riesgo', 'peligro', 'inseguro', 'sucio', 'abandono',
    'cierre', 'cierran', 'despido', 'despidos', 'semana santa', 'procesión', 'religión', 'iglesia', 'culto'
}

NEGACIONES = {'no', 'ni', 'nunca', 'tampoco', 'sin'}

def heuristic_fallback(text):
    if not text: return 'neutral', 0.0, 'Sociedad'
    words = re.findall(r'\w+', text.lower())
    pos_count = 0; neg_count = 0
    for i, word in enumerate(words):
        if word in PALABRAS_POSITIVAS:
            if i > 0 and words[i-1] in NEGACIONES: neg_count += 1
            else: pos_count += 1
        elif word in PALABRAS_NEGATIVAS:
            if i > 0 and words[i-1] in NEGACIONES: pos_count += 1
            else: neg_count += 1
    total = pos_count + neg_count
    if total == 0: return 'neutral', 0.0, 'Sociedad'
    score = (pos_count - neg_count) / total
    if score > 0.05: return 'positiva', score, 'Sociedad'
    elif score < -0.05: return 'negativa', score, 'Sociedad'
    else: return 'neutral', score, 'Sociedad'

def analyze_sentiment(text):
    """
    Analiza el sentimiento y la categoría de un texto usando Groq Llama 3.3.
    Retorna (sentimiento, score, categoria).
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.environ.get("groq_KEY") or os.environ.get("GROQ_API_KEY")
        if not api_key:
            return heuristic_fallback(text)
            
        client = Groq(api_key=api_key)
        
        system_prompt = '''Eres un clasificador experto de noticias de Vitoria-Gasteiz para un portal local.
        Dado un texto, debes extraer:
        1. "sentiment": positiva, negativa, o neutral (basado en el tono y las implicaciones del evento).
        2. "category": una sola categoría entre:
           - Sociedad: Huelgas, sucesos, barrios (Zabalgana, Salburua).
           - Política: Ayuntamiento, Diputación de Álava, elecciones.
           - Deportes: Alavés, Baskonia, maratones, pelota vasca.
           - Cultura: Magialdia, Festival de Jazz, eventos en el Iradier Arena.
           - Urbanismo: Obras del BEI, tranvía, Anillo Verde.
           Si no encaja en ninguna, usa "Otros".
        
        Responde estrictamente con un JSON válido que contenga sólamente esas dos claves.
        
        IMPORTANTE: Cualquier noticia relacionada con temas religiosos, procesiones, Semana Santa, festividades religiosas o cultos DEBE ser marcada como "negativa", independientemente de si el tono del texto parece positivo o neutral.
        '''
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text[:1500]}
            ],
            temperature=0, # Para máxima predictibilidad
            max_tokens=100,
            response_format={"type": "json_object"}
        )
        
        result_str = completion.choices[0].message.content
        data = json.loads(result_str)
        sentiment = data.get("sentiment", "neutral").lower()
        if sentiment not in ["positiva", "negativa", "neutral"]:
            sentiment = "neutral"
            
        category = data.get("category", "Sociedad")
        if category not in ["Sociedad", "Política", "Deportes", "Cultura", "Urbanismo", "Otros"]:
            category = "Otros"
            
        # Puntación simple basada en la salida del modelo
        score = 1.0 if sentiment == 'positiva' else (-1.0 if sentiment == 'negativa' else 0.0)
        
        return sentiment, score, category
    except Exception as e:
        print(f"Error clasificando con Groq: {e}. Usando fallback heurístico.")
        return heuristic_fallback(text)

def translate_to_euskara(title, body):
    """
    Traduce el título y cuerpo de una noticia al euskara usando Groq llama-3.1-8b-instant.
    Retorna (title_eu, body_eu) o (None, None) si falla.
    """
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            # Recolectar todas las posibles claves que existan en el env
            keys = [
                os.environ.get("GROQ_TRANSLATION_KEY"),
                os.environ.get("GROQ_API_KEY"),
                os.environ.get("GROQ_API_KEY_2"),
                os.environ.get("GROQ_API_KEY_3"),
                os.environ.get("groq_KEY")
            ]
            valid_keys = [k for k in keys if k]
            
            if not valid_keys:
                print("Error: No se encontró ninguna clave de API de Groq en el entorno.")
                return None, None
                
            # Rotar la clave según el número de intento actual
            api_key = valid_keys[attempt % len(valid_keys)]
            client = Groq(api_key=api_key)
            
            # Truncate body at last sentence boundary before 2000 chars to ensure stable JSON output
            body_truncated = body[:2000]
            last_period = body_truncated.rfind('.')
            if last_period > 300:
                body_truncated = body_truncated[:last_period + 1]
            combined = f"TITLE: {title}\n\nBODY:\n{body_truncated}"
            
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant", # Optimized for scale
                messages=[
                    {"role": "system", "content": "Itzuli testu hauek EUSKARARA. Erantzun JSON FORMATUAN soilik: {\"title_eu\": \"...\", \"body_eu\": \"...\"}. Ez idatzi azalpenik."},
                    {"role": "user", "content": f"ITZULI TESTU HAU EUSKARARA ORAIN:\n\n{combined}"}
                ],
                temperature=0.0,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            
            result_str = completion.choices[0].message.content
            data = json.loads(result_str)
            return data.get("title_eu"), data.get("body_eu")
        except Exception as e:
            print(f"Error traduciendo al euskara (intento {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(retry_delay)
            else:
                return None, None

def translate_to_polish(title, body):
    """
    Traduce el título y cuerpo de una noticia al polaco usando Groq llama-3.3-70b-versatile.
    Retorna (title_pl, body_pl) o (None, None) si falla.
    """
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            from dotenv import load_dotenv
            load_dotenv()
            # Recolectar todas las posibles claves que existan en el env
            keys = [
                os.environ.get("GROQ_POLISH_KEY"),
                os.environ.get("GROQ_TRANSLATION_KEY"),
                os.environ.get("GROQ_API_KEY"),
                os.environ.get("GROQ_API_KEY_2"),
                os.environ.get("GROQ_API_KEY_3"),
                os.environ.get("groq_KEY")
            ]
            valid_keys = [k for k in keys if k]
            
            if not valid_keys:
                print("Error: No se encontró ninguna clave de API de Groq para polaco en el entorno.")
                return None, None
                
            # Rotar la clave según el número de intento actual
            api_key = valid_keys[attempt % len(valid_keys)]
            client = Groq(api_key=api_key)
            
            # Truncate body at last sentence boundary before 2000 chars
            body_truncated = body[:2000]
            last_period = body_truncated.rfind('.')
            if last_period > 300:
                body_truncated = body_truncated[:last_period + 1]
            combined = f"TITLE: {title}\n\nBODY:\n{body_truncated}"
            
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant", # Optimized for scale
                messages=[
                    {"role": "system", "content": "Przetłumacz te teksty na JĘZYK POLSKI. Odpowiedz wyłącznie w formacie JSON: {\"title_pl\": \"...\", \"body_pl\": \"...\"}. Nie dodawaj wyjaśnień."},
                    {"role": "user", "content": f"PRZETŁUMACZ TEN TEKST NA POLSKI TERAZ:\n\n{combined}"}
                ],
                temperature=0.0,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            
            result_str = completion.choices[0].message.content
            data = json.loads(result_str)
            return data.get("title_pl"), data.get("body_pl")
        except Exception as e:
            print(f"Error en traducción al polaco (intento {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(retry_delay)
            else:
                return None, None

def rewrite_article(title, body):
    """
    Reescribe el título y cuerpo de una noticia en castellano con diferente estilo
    para evitar problemas de copyright, manteniendo todos los hechos veraces.
    Prioriza el detalle y una extensión similar al original.
    """
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            keys = [
                os.environ.get("GROQ_REWRITE_KEY"),
                os.environ.get("GROQ_API_KEY"),
                os.environ.get("GROQ_API_KEY_2"),
                os.environ.get("GROQ_API_KEY_3"),
                os.environ.get("groq_KEY")
            ]
            valid_keys = [k for k in keys if k]
            
            if not valid_keys:
                print("Error: No se encontró clave API para reescribir artículos.")
                return None, None

            api_key = valid_keys[attempt % len(valid_keys)]
            client = Groq(api_key=api_key)

            # Truncate at last sentence boundary before 5000 chars (much more detail)
            body_truncated = body[:5000]
            last_period = body_truncated.rfind('.')
            if last_period > 300:
                body_truncated = body_truncated[:last_period + 1]

            combined = f"TÍTULO: {title}\n\nCUERPO:\n{body_truncated}"

            system_prompt = """Eres un redactor periodístico profesional de Vitoria-Gasteiz. Tu tarea es reescribir noticias para un portal local manteniendo la máxima fidelidad y detalle del original.

REGLAS CRÍTICAS:
1. NO RESUMAS: Si el original es largo, el reescrito debe ser largo. Si hay 8 párrafos, mantén aproximadamente 8 párrafos.
2. DETALLE TOTAL: No omitas información, testimonios, matices o datos secundarios. Mantenlos todos.
3. DATOS PRECISOS: Nombres, fechas, lugares y cifras deben ser EXACTAMENTE iguales.
4. ESTILO ORIGINAL: Cambia la estructura de las frases y usa sinónimos para evitar el plagio literal, pero conserva el sentido y la "cercanía" de la fuente.
5. IDIOMA: Íntegramente en CASTELLANO.

Responde ÚNICAMENTE con el objeto JSON: {"title_rewritten": "...", "body_rewritten": "..."}"""

            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": combined}
                ],
                temperature=0.2, # Un poco más alto para variar el estilo sin perder precisión
                max_tokens=6144, # Suficiente para artículos largos
                response_format={"type": "json_object"}
            )

            result_str = completion.choices[0].message.content
            data = json.loads(result_str)
            return data.get("title_rewritten"), data.get("body_rewritten")
        except Exception as e:
            print(f"Error reescribiendo artículo (intento {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(retry_delay)
            else:
                return None, None

if __name__ == "__main__":
    test_text = "El Deportivo Alaés inaugura un nuevo campo de entrenamiento y mejora sus instalaciones."
    print(f"Test positivo: {analyze_sentiment(test_text)}")
