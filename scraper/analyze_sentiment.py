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
            api_key = os.environ.get("GROQ_TRANSLATION_KEY")
            if not api_key:
                print("Error: No se encontró GROQ_TRANSLATION_KEY en el entorno.")
                return None, None
                
            client = Groq(api_key=api_key)
            
            # Truncate body at last sentence boundary before 2000 chars to ensure stable JSON output
            body_truncated = body[:2000]
            last_period = body_truncated.rfind('.')
            if last_period > 300:
                body_truncated = body_truncated[:last_period + 1]
            combined = f"TITLE: {title}\n\nBODY:\n{body_truncated}"
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": """Zara euskarazko itzultzaile automatiko profesionala. 
    Zure helburua TITLE eta BODY testuak GAZTELANIATIK EUSKARARA itzultzea da.

    ARAURIK GARRANTZITSUENAK:
    1. ERANTZUN BAKARRIK EUSKARAZ. Ez erabili gaztelaniazko hitzik (ezta "Vitoria" ordez "Gasteiz" baizik, ezta "un" ordez "bat", etab).
    2. Ez nahasi hizkuntzak. Itzulpenak profesionala eta naturala izan behar du, baina %100 EUSKARAZ.
    3. ZEHAZTASUNA: Ziurtatu hitz teknikoak eta adjektiboak zuzenak direla (adibidez, "decaido" -> "goibel" itzuli behar da, ez "dekaitua").
    4. Erantzun formatu honetan soilik (JSON): {"title_eu": "...", "body_eu": "..."}
    5. Ez idatzi azalpenik."""},
                    {"role": "user", "content": f"ITZULI TESTU HAU EUSKARARA ORAIN:\n\n{combined}"}
                ],
                temperature=0.0,
                max_tokens=6000,
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
            api_key = os.environ.get("GROQ_POLISH_KEY")
            if not api_key:
                print("Error: No se encontró GROQ_POLISH_KEY en el entorno.")
                return None, None
                
            client = Groq(api_key=api_key)
            
            # Truncate body at last sentence boundary before 2000 chars
            body_truncated = body[:2000]
            last_period = body_truncated.rfind('.')
            if last_period > 300:
                body_truncated = body_truncated[:last_period + 1]
            combined = f"TITLE: {title}\n\nBODY:\n{body_truncated}"
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": """Jesteś profesjonalnym tłumaczem automatycznym na język polski. 
    Twoim celem jest przetłumaczenie tekstów TITLE i BODY z JĘZYKA HISZPAŃSKIEGO na JĘZYK POLSKI.

    NAJWAŻNIEJSZE ZASADY:
    1. ODPOWIADAJ WYŁĄCZNIE W JĘZYKU POLSKIM. Nie używaj hiszpańskich słów.
    2. Zachowaj profesjonalny, dziennikarski styl (polska szkoła reportażu).
    3. Nie mieszaj języków. Tłumaczenie musi być naturalne i w 100% po polsku.
    4. Odpowiedz wyłącznie w formacie JSON: {"title_pl": "...", "body_pl": "..."}
    5. Nie dodawaj żadnych wyjaśnień."""},
                    {"role": "user", "content": f"PRZETŁUMACZ TEN TEKST NA POLSKI TERAZ:\n\n{combined}"}
                ],
                temperature=0.0,
                max_tokens=6000,
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
    Usa GROQ_REWRITE_KEY y llama-3.1-8b-instant.
    Retorna (title_rewritten, body_rewritten) o (None, None) si falla.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.environ.get("GROQ_REWRITE_KEY")
        if not api_key:
            return None, None

        client = Groq(api_key=api_key)

        # Truncate at last sentence boundary before 2000 chars
        body_truncated = body[:2000]
        last_period = body_truncated.rfind('.')
        if last_period > 300:
            body_truncated = body_truncated[:last_period + 1]

        combined = f"TÍTULO: {title}\n\nCUERPO:\n{body_truncated}"

        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": """Eres un redactor periodístico profesional. Tu tarea es reescribir noticias para un portal local.

REGLAS CRÍTICAS:
- MANTÉN TODOS LOS DATOS (nombres, fechas, números) EXACTAMENTE IGUAL.
- Reescribe el estilo: cambia la estructura de las frases y el vocabulario.
- PROHIBIDO copiar frases literales del original.
- El resultado debe estar íntegramente en CASTELLANO.
- Responde ÚNICAMENTE con el objeto JSON: {"title_rewritten": "...", "body_rewritten": "..."}"""},
                {"role": "user", "content": combined}
            ],
            temperature=0.0,
            max_tokens=6000,
            response_format={"type": "json_object"}
        )

        result_str = completion.choices[0].message.content
        data = json.loads(result_str)
        return data.get("title_rewritten"), data.get("body_rewritten")
    except Exception as e:
        print(f"Error reescribiendo artículo: {e}")
        return None, None

if __name__ == "__main__":
    test_text = "El Deportivo Alaés inaugura un nuevo campo de entrenamiento y mejora sus instalaciones."
    print(f"Test positivo: {analyze_sentiment(test_text)}")
