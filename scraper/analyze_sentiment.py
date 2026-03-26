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
    'cierre', 'cierran', 'despido', 'despidos'
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
        
        Responde estrictamente con un JSON válido que contenga sólamente esas dos claves.'''
        
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
    try:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.environ.get("GROQ_TRANSLATION_KEY")
        if not api_key:
            return None, None
            
        client = Groq(api_key=api_key)
        
        # Truncate body at last sentence boundary before 3000 chars so translation is coherent
        body_truncated = body[:3000]
        last_period = body_truncated.rfind('.')
        if last_period > 500:  # Only cut at period if it's not too early
            body_truncated = body_truncated[:last_period + 1]
        combined = f"TITLE: {title}\n\nBODY:\n{body_truncated}"
        
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": """Zara euskarako itzultzaile profesional bat. Testuak gaztelaniatik euskarara itzuli behar dituzu, hizkuntza naturalak erabiliz.

Arauak:
- Itzuli TITLE eta BODY bereizita
- Jatorrizko formatua mantendu
- Responde BETI JSON formatuan, honela: {\"title_eu\": \"...\", \"body_eu\": \"...\"}
- ez erantsi azalpenik, JSON soilik"""},
                {"role": "user", "content": combined}
            ],
            temperature=0.2,
            max_tokens=6000,
            response_format={"type": "json_object"}
        )
        
        result_str = completion.choices[0].message.content
        data = json.loads(result_str)
        return data.get("title_eu"), data.get("body_eu")
    except Exception as e:
        print(f"Error traduciendo al euskara: {e}")
        return None, None

if __name__ == "__main__":
    test_text = "El Deportivo Alaés inaugura un nuevo campo de entrenamiento y mejora sus instalaciones."
    print(f"Test positivo: {analyze_sentiment(test_text)}")

