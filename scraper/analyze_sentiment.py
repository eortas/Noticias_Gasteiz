import re
import os
import json
import time
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

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
    """Analiza sentimiento y categoría usando Llama 70b con pool de llaves."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            keys = [
                os.environ.get("GROQ_REWRITE_2"), os.environ.get("GROQ_REWRITE_3"),
                os.environ.get("GROQ_REWRITE_KEY"), os.environ.get("groq_KEY"), 
                os.environ.get("GROQ_API_KEY"), os.environ.get("GROQ_TRANSLATION_KEY")
            ]
            valid_keys = [k for k in keys if k]
            api_key = valid_keys[(attempt + int(time.time())) % len(valid_keys)]
            
            client = Groq(api_key=api_key)
            system_prompt = """Eres un clasificador experto de noticias de Vitoria-Gasteiz.
            Responde ÚNICAMENTE en JSON: {"sentiment": "positiva/negativa/neutral", "score": -1.0 a 1.0, "category": "Política/Economía/Sociedad/Deportes/Cultura/Sucesos/Urbanismo"}"""
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text[:1000]}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            data = json.loads(completion.choices[0].message.content)
            return data.get('sentiment', 'neutral'), data.get('score', 0.0), data.get('category', 'Sociedad')
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Error clasificando con Groq: {e}. Usando fallback heurístico.")
                return heuristic_fallback(text)
            time.sleep(2)

def translate_to_euskara(title, body):
    return _translate_full(title, body, "EUSKARA", "title_eu", "body_eu")

def translate_to_polish(title, body):
    return _translate_full(title, body, "POLACO", "title_pl", "body_pl")

def _translate_full(title, body, lang_label, title_key, body_key):
    title_tr = _translate_chunk(title, "TÍTULO", lang_label, title_key)
    chunks = _split_text(body, 3000)
    translated_chunks = []
    for i, chunk in enumerate(chunks):
        print(f"      - Traduciendo fragmento de {lang_label.lower()} {i+1}/{len(chunks)}...")
        tr_chunk = _translate_chunk(chunk, "CUERPO", lang_label, body_key)
        translated_chunks.append(tr_chunk or chunk)
        if len(chunks) > 1: time.sleep(1)
    return title_tr, "\n\n".join(translated_chunks)

def _translate_chunk(text, type_label, target_lang, json_key):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            keys = [
                os.environ.get("GROQ_REWRITE_2"), os.environ.get("GROQ_REWRITE_3"),
                os.environ.get("GROQ_TRANSLATION_KEY"), os.environ.get("GROQ_POLISH_KEY"), 
                os.environ.get("GROQ_EUSKERA2"), os.environ.get("GROQ_API_KEY")
            ]
            valid_keys = [k for k in keys if k]
            api_key = valid_keys[(attempt + int(time.time())) % len(valid_keys)]
            client = Groq(api_key=api_key)
            
            system_prompt = f"Przetłumacz ten {type_label} na JĘZYK POLSKI. Odpowiedz wyłącznie w formacie JSON: {{\"{json_key}\": \"...\"}}" if "POL" in target_lang else f"Itzuli {type_label} hau EUSKARA. Erantzun JSON FORMATUAN soilik: {{\"{json_key}\": \"...\"}}"
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            return json.loads(completion.choices[0].message.content).get(json_key)
        except:
            if attempt < max_retries - 1: time.sleep(2)
    return None

def rewrite_article(title, body):
    title_rw = _rewrite_chunk(title, "TÍTULO")
    chunks = _split_text(body, 3500)
    rewritten_chunks = []
    for i, chunk in enumerate(chunks):
        print(f"      - Reescribiendo fragmento {i+1}/{len(chunks)}...")
        rw_chunk = _rewrite_chunk(chunk, "CUERPO")
        rewritten_chunks.append(rw_chunk or chunk)
        if len(chunks) > 1: time.sleep(1)
    return title_rw, "\n\n".join(rewritten_chunks)

def _rewrite_chunk(text, type_label):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            keys = [
                os.environ.get("GROQ_REWRITE_2"), os.environ.get("GROQ_REWRITE_3"),
                os.environ.get("GROQ_REWRITE_KEY"), os.environ.get("groq_KEY"), os.environ.get("GROQ_API_KEY")
            ]
            valid_keys = [k for k in keys if k]
            api_key = valid_keys[(attempt + int(time.time())) % len(valid_keys)]
            client = Groq(api_key=api_key)
            
            json_key = "title_rewritten" if type_label == "TÍTULO" else "body_rewritten"
            system_prompt = f"""Eres el Jefe de Redacción de un diario líder en Vitoria-Gasteiz. 
            Tu misión es REESCRIBIR este {type_label} de forma ÍNTEGRA, DETALLADA y EXTENSA.
            
            REGLAS DE ORO:
            1. PROHIBIDO RESUMIR O ACORTAR. El texto resultante debe ser tan largo como el original.
            2. MANTÉN EL MISMO NÚMERO DE PÁRRAFOS. Usa DOBLE SALTO DE LÍNEA (\\n\\n) entre ellos.
            3. INCLUYE todos los nombres propios, cifras, cargos y citas textuales sin excepción.
            4. Cambia el vocabulario y estilo para que sea 100% original.
            
            Responde ÚNICAMENTE en formato JSON: {{"{json_key}": "..."}}"""

            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            rewritten = json.loads(completion.choices[0].message.content).get(json_key)
            
            # Validación de longitud: si se ha comido más del 25% del texto, forzamos reintento
            if rewritten and attempt < 2 and type_label == "CUERPO" and len(rewritten) < len(text) * 0.75:
                print(f"      ! Reescritura demasiado corta ({len(rewritten)} vs {len(text)}), forzando más detalle...")
                continue

            if rewritten and attempt == 0 and len(text) > 50:
                words_orig = set(re.findall(r'\w+', text.lower())); words_rw = set(re.findall(r'\w+', rewritten.lower()))
                if len(words_orig) > 0 and (len(words_orig & words_rw) / len(words_orig)) > 0.75:
                    print(f"      ! Reescritura demasiado similar, forzando creatividad..."); continue
            return rewritten
        except:
            if attempt < max_retries - 1: time.sleep(2)
    return None

def _split_text(text, max_chars):
    if not text: return []
    chunks = []
    while text:
        if len(text) <= max_chars: chunks.append(text); break
        split_at = text.rfind('\n', 0, max_chars)
        if split_at == -1: split_at = text.rfind('. ', 0, max_chars)
        if split_at == -1 or split_at < max_chars * 0.5: split_at = max_chars
        chunks.append(text[:split_at].strip())
        text = text[split_at:].strip()
    return chunks
