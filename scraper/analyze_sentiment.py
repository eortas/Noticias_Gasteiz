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
    Traduce el título y cuerpo de una noticia al euskara usando Groq.
    Si el cuerpo es muy largo, lo divide en fragmentos (chunks) para traducirlo completo.
    """
    # Traducir el título primero
    title_eu = _translate_chunk(title, "TITLE", "EUSKARARA", "title_eu")
    
    # Dividir el cuerpo en fragmentos de unos 3500 caracteres
    chunks = _split_text(body, 3500)
    translated_chunks = []
    
    for i, chunk in enumerate(chunks):
        print(f"      - Traduciendo fragmento de euskara {i+1}/{len(chunks)}...")
        translated_chunk = _translate_chunk(chunk, "BODY", "EUSKARARA", "body_eu")
        if translated_chunk:
            translated_chunks.append(translated_chunk)
        else:
            # Si falla un fragmento, intentamos continuar o usamos el original como fallback
            translated_chunks.append(chunk)
        
        if len(chunks) > 1:
            import time
            time.sleep(2) # Evitar TPM limit entre fragmentos

    return title_eu, "\n\n".join(translated_chunks)

def translate_to_polish(title, body):
    """
    Traduce el título y cuerpo de una noticia al polaco usando Groq.
    Si el cuerpo es muy largo, lo divide en fragmentos (chunks) para traducirlo completo.
    """
    # Traducir el título primero
    title_pl = _translate_chunk(title, "TITLE", "POLACO", "title_pl")
    
    # Dividir el cuerpo en fragmentos de unos 3500 caracteres
    chunks = _split_text(body, 3500)
    translated_chunks = []
    
    for i, chunk in enumerate(chunks):
        print(f"      - Traduciendo fragmento de polaco {i+1}/{len(chunks)}...")
        translated_chunk = _translate_chunk(chunk, "BODY", "JĘZYK POLSKI", "body_pl")
        if translated_chunk:
            translated_chunks.append(translated_chunk)
        else:
            translated_chunks.append(chunk)
        
        if len(chunks) > 1:
            import time
            time.sleep(2)

    return title_pl, "\n\n".join(translated_chunks)

def _split_text(text, max_chars):
    """Divide un texto en fragmentos intentando no romper párrafos."""
    if not text: return []
    if len(text) <= max_chars: return [text]
    
    chunks = []
    while text:
        if len(text) <= max_chars:
            chunks.append(text)
            break
        
        # Buscar el último punto o salto de línea antes del límite
        split_at = text.rfind('\n', 0, max_chars)
        if split_at == -1:
            split_at = text.rfind('. ', 0, max_chars)
            if split_at != -1: split_at += 1
            
        if split_at == -1 or split_at < max_chars * 0.5:
            split_at = max_chars # Forzar corte si no hay buen punto
            
        chunks.append(text[:split_at].strip())
        text = text[split_at:].strip()
    return chunks

def _translate_chunk(text, type_label, target_lang, json_key):
    """Helper para traducir un fragmento individual."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            from dotenv import load_dotenv
            load_dotenv()
            keys = [
                os.environ.get("GROQ_TRANSLATION_KEY"),
                os.environ.get("GROQ_POLISH_KEY"),
                os.environ.get("GROQ_EUSKERA2"),
                os.environ.get("GROQ_API_KEY"),
                os.environ.get("groq_KEY")
            ]
            valid_keys = [k for k in keys if k]
            api_key = valid_keys[(attempt + int(time.time()) % 10) % len(valid_keys)]
            
            from groq import Groq
            client = Groq(api_key=api_key)
            
            system_prompt = f"Itzuli {type_label} hau {target_lang}. Erantzun JSON FORMATUAN soilik: {{\"{json_key}\": \"...\"}}. Ez idatzi azalpenik. Itzuli testu osoa zehatz-mehatz."
            if "POL" in target_lang:
                system_prompt = f"Przetłumacz ten {type_label} na JĘZYK POLSKI. Odpowiedz wyłącznie w formacie JSON: {{\"{json_key}\": \"...\"}}. Nie dodawaj wyjaśnień."

            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"ITZULI ORAIN:\n\n{text}"}
                ],
                temperature=0.0,
                max_tokens=3000, # Reducido para evitar TPM limit
                response_format={"type": "json_object"}
            )
            
            result_str = completion.choices[0].message.content
            data = json.loads(result_str)
            return data.get(json_key)
        except Exception as e:
            if attempt < max_retries - 1:
                import time
                time.sleep(3)
            else:
                return None

def rewrite_article(title, body):
    """
    Reescribe el título y cuerpo de una noticia en castellano con diferente estilo
    para evitar problemas de copyright, manteniendo todos los hechos veraces.
    """
    # Reescribir el título
    title_rw = _rewrite_chunk(title, "TÍTULO")
    
    # Dividir el cuerpo en fragmentos para reescribir completo
    chunks = _split_text(body, 3500)
    rewritten_chunks = []
    
    for i, chunk in enumerate(chunks):
        print(f"      - Reescribiendo fragmento {i+1}/{len(chunks)}...")
        rw_chunk = _rewrite_chunk(chunk, "CUERPO")
        if rw_chunk:
            rewritten_chunks.append(rw_chunk)
        else:
            rewritten_chunks.append(chunk)
            
        if len(chunks) > 1:
            import time
            time.sleep(2)

    return title_rw, "\n\n".join(rewritten_chunks)

def _rewrite_chunk(text, type_label):
    """Helper para reescribir un fragmento individual."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            from dotenv import load_dotenv
            load_dotenv()
            keys = [
                os.environ.get("GROQ_REWRITE_KEY"),
                os.environ.get("GROQ_API_KEY"),
                os.environ.get("groq_KEY")
            ]
            valid_keys = [k for k in keys if k]
            api_key = valid_keys[(attempt + int(time.time()) % 10) % len(valid_keys)]
            
            from groq import Groq
            client = Groq(api_key=api_key)

            json_key = "title_rewritten" if type_label == "TÍTULO" else "body_rewritten"
            system_prompt = f"""Eres un redactor periodístico profesional de Vitoria-Gasteiz. Reescribe este {type_label} manteniendo la máxima fidelidad y detalle. 
            NO RESUMAS. Íntegramente en CASTELLANO. 
            Responde ÚNICAMENTE con el objeto JSON: {{"{json_key}": "..."}}"""

            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.2,
                max_tokens=3000,
                response_format={"type": "json_object"}
            )

            result_str = completion.choices[0].message.content
            data = json.loads(result_str)
            return data.get(json_key)
        except Exception as e:
            if attempt < max_retries - 1:
                import time
                time.sleep(3)
            else:
                return None

if __name__ == "__main__":
    test_text = "El Deportivo Alaés inaugura un nuevo campo de entrenamiento y mejora sus instalaciones."
    print(f"Test positivo: {analyze_sentiment(test_text)}")
