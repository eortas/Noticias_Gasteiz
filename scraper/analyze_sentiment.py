import re
import os
import json
import random
import time
from groq import Groq
from mistralai.client.sdk import Mistral
from dotenv import load_dotenv
from key_rotator import get_next_key
from grammar_cleaner import fix_grammar_errors

load_dotenv()

# Diccionarios para análisis heurístico de sentimientos
PALABRAS_POSITIVAS = {
    'bueno', 'buena', 'buenos', 'buenas', 'mejor', 'mejores', 'excelente', 'excelentes', 'positivo', 'positiva', 
    'éxito', 'éxitos', 'logro', 'logros', 'avanza', 'avanzan', 'mejora', 'mejoras', 
    'beneficio', 'beneficios', 'alegría', 'feliz', 'felices', 'oportunidad', 'oportunidades', 'crecimiento', 
    'esperanza', 'solución', 'soluciones', 'paz', 'seguro', 'segura', 'impulsa', 'impulsan', 'apoyo', 
    'vanguardia', 'moderno', 'moderna', 'eficiente', 'gratis', 'estrena', 'estrenan', 'inaugura', 'inauguran', 
    'lidera', 'brilla', 'talento', 'unión', 'solidario', 'solidaria', 'relevo', 'continuidad', 
    'tradición', 'familia', 'futuro', 'crean', 'vuelve', 'vuelven', 'abre', 'abren',
    'fiesta', 'fiestas', 'música', 'celebración', 'celebraciones', 'concierto', 'conciertos', 
    'diversión', 'danza', 'baile', 'deporte', 'deportes', 'gastronomía', 'popular', 'populares',
    'homenaje', 'premio', 'premios', 'galardón', 'galardones', 'triunfo', 'triunfos', 'victoria', 'victorias'
}

PALABRAS_NEGATIVAS = {
    'malo', 'mala', 'malos', 'malas', 'peor', 'peores', 'negativo', 'negativa', 'fracaso', 'error', 'problema', 
    'problemas', 'crisis', 'daño', 'daños', 'muerte', 'muertes', 'fallece', 'fallecen', 'fallecido', 'fallecida',
    'accidente', 'accidentes', 'robo', 'robos', 'robar', 'robado', 'robada', 'robados', 'robadas', 'robarle', 'robarles',
    'atraco', 'atracos', 'atracar', 'atracador', 'atracadores', 'hurto', 'hurtos', 'hurtar', 'sustraer', 'sustracción',
    'detenido', 'detenidos', 'detenida', 'detenidas', 'agresión', 'agresiones', 'agredir', 'agresor', 'agresores',
    'pelea', 'peleas', 'herido', 'herida', 'heridos', 'heridas', 'lesionado', 'lesionada', 'lesionados', 'lesionadas',
    'lesión', 'lesiones', 'fractura', 'fracturas', 'paliza', 'palizas', 'golpe', 'golpes', 'golpear', 'golpeado', 'golpeada',
    'asesinato', 'asesinados', 'matar', 'apuñalado', 'apuñalada', 'apuñalar', 'apuñalamiento', 'navajazo',
    'denuncia', 'denuncias', 'corte', 'huelga', 'huelgas', 'protesta', 'protestas', 'incendio', 'incendios', 
    'atropello', 'atropellos', 'crimen', 'crímenes', 'estafa', 'estafas', 'pérdida', 'pérdidas', 'caída', 'baja', 
    'tensión', 'riesgo', 'riesgos', 'peligro', 'peligros', 'inseguro', 'inseguridad', 'sucio', 'abandono',
    'cierre', 'cierran', 'despido', 'despidos', 'rechazo', 'rechazos', 'oposición', 'enfrentamiento', 'enfrentamientos',
    'delito', 'delitos', 'delincuente', 'delincuencia', 'víctima', 'victima', 'víctimas', 'victimas', 'violencia', 'violento',
    'bochorno', 'canícula', 'sequía', 'sequia', 'asfixiante', 'saturación', 'saturado', 'saturada', 'saturados', 'saturadas'
}

FRASES_NEGATIVAS = [
    'ola de calor', 'olas de calor', 'calor extremo', 'golpe de calor', 'golpes de calor',
    'alerta por calor', 'temperaturas extremas', 'calor asfixiante', 'calor sofocante',
    'elevadas temperaturas', 'altas temperaturas', 'temperaturas elevadas', 'exceso de calor',
    'calor intenso', 'intenso calor', 'el calor dispara', 'bochorno',
    'alerta amarilla por calor', 'alerta naranja por calor', 'alerta roja por calor',
    'intento de robo', 'intentan robarle', 'intento de hurto', 'robarle el móvil', 'robar el móvil',
    'agresión física', 'brutal agresión', 'violencia callejera', 'rompen la nariz'
]

NEGACIONES = {'no', 'ni', 'nunca', 'tampoco', 'sin'}

def clean_thinking_tags(text):
    """Elimina bloques <think>...</think> que genera Qwen en modo thinking."""
    if not text:
        return text
    return re.sub(r'<think>[\s\S]*?(?:</think>|$)', '', text).strip()

def heuristic_fallback(text):
    """Calcula el sentimiento mediante análisis heurístico de términos positivos, negativos y frases complejas."""
    if not text:
        return 'neutral', 0.0, 'Sociedad'
    
    text_lower = text.lower()
    pos_count = 0
    neg_count = 0
    
    # Verificamos coincidencias en frases compuestas de fuerte impacto negativo (como robos o eventos climáticos)
    for frase in FRASES_NEGATIVAS:
        if frase in text_lower:
            neg_count += 2

    words = re.findall(r'\w+', text_lower)
    for i, word in enumerate(words):
        if word in PALABRAS_POSITIVAS:
            if i > 0 and words[i-1] in NEGACIONES:
                neg_count += 1
            else:
                pos_count += 1
        elif word in PALABRAS_NEGATIVAS:
            if i > 0 and words[i-1] in NEGACIONES:
                pos_count += 1
            else:
                neg_count += 1

    total = pos_count + neg_count
    # Si la presencia de términos es muy escasa, dejamos que la IA tome la decisión
    if total <= 1:
        return 'neutral', 0.0, 'Sociedad'
    
    score = (pos_count - neg_count) / total
    if score > 0.05:
        return 'positiva', round(score, 4), 'Sociedad'
    elif score < -0.05:
        return 'negativa', round(score, 4), 'Sociedad'
    else:
        return 'neutral', round(score, 4), 'Sociedad'

def analyze_sentiment(text):
    """Analiza sentimiento y categoría. Primero pasa por el modelo heurístico y, si es neutral, pasa por la IA."""
    # 1. Analizamos con la heurística primero
    heur_sentiment, heur_score, heur_category = heuristic_fallback(text)
    if heur_sentiment in ('positiva', 'negativa'):
        return heur_sentiment, heur_score, heur_category
        
    # 2. Si el resultado es neutral, pasamos a consultar el modelo de IA
    max_retries = 3
    for attempt in range(max_retries):
        try:
            keys = [
                os.environ.get("GROQ_REWRITE_2"), os.environ.get("GROQ_REWRITE_3"),
                os.environ.get("GROQ_REWRITE_KEY"), os.environ.get("groq_KEY"), 
                os.environ.get("GROQ_TRANSLATION_KEY"), os.environ.get("GROQ_POLISH_KEY"),
                os.environ.get("GROQ_EUSKERA2"), os.environ.get("GROQ_POLISH2"),
                os.environ.get("GROQ_API_KEY")
            ]
            keys.extend(get_extra_keys())
            valid_keys = [k for k in keys if k]
            if not valid_keys:
                return heur_sentiment, heur_score, heur_category
                
            api_key = get_next_key(valid_keys, "sentiment")
            
            client = Groq(api_key=api_key)
            system_prompt = """Eres un clasificador experto de sentimiento para noticias de Vitoria-Gasteiz y Álava.
Evalúa objetivamente si la noticia transmite un impacto positivo, negativo o neutral para la ciudadanía.
- Noticias de celebraciones, fiestas, victorias deportivas, mejoras de servicios o eventos comunitarios son POSITIVAS.
- Noticias de delitos (robos, agresiones, atracos, palizas), accidentes, alertas de salud/meteorológicas (olas de calor, incendios) son NEGATIVAS.
Responde ÚNICAMENTE en JSON: {"sentiment": "positiva/negativa/neutral", "score": -1.0 a 1.0, "category": "Política/Economía/Sociedad/Deportes/Cultura/Sucesos/Urbanismo"}"""
            
            completion = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text[:1000]}],
                temperature=0.1,
                response_format={"type": "json_object"},
                extra_body={"reasoning_effort": "none"}
            )
            raw_response = clean_thinking_tags(completion.choices[0].message.content)
            data = json.loads(raw_response)
            return data.get('sentiment', 'neutral'), data.get('score', 0.0), data.get('category', 'Sociedad')
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Error clasificando con Groq: {e}. Usamos el resultado heurístico original.")
                return heur_sentiment, heur_score, heur_category
            time.sleep(2)


def sanitize_media_references(text):
    """
    Reemplaza menciones explícitas a medios de comunicación por expresiones neutras como 'este medio'.
    """
    if not text:
        return text
    
    # Lista de tuplas con (patrón_regex, reemplazo)
    # Buscamos variaciones comunes de los nombres de los medios con límites de palabra (\b)
    replacements = [
        (r'\bDiario de Noticias de [Áá]lava\b', 'este medio'),
        (r'\bDiario de Noticias\b', 'este medio'),
        (r'\bNoticias de [Áá]lava\b', 'este medio'),
        (r'\bEl Correo de [Áá]lava\b', 'este medio'),
        (r'\bEl Correo\b', 'este medio'),
        (r'\bGasteiz\s*Hoy\b', 'este medio'),
        (r'\bGasteizHoy\b', 'este medio'),
        (r'\bDiario de [Áá]lava\b', 'este medio')
    ]
    
    sanitized = text
    for pattern, repl in replacements:
        sanitized = re.sub(pattern, repl, sanitized, flags=re.IGNORECASE)
        
    return sanitized


def rewrite_article(title, body):
    """Reescribe un artículo completo, manejando el título y el cuerpo por fragmentos de párrafos."""
    title_rw = _rewrite_chunk(title, "TÍTULO")
    if title_rw:
        title_rw = title_rw.split('\n')[0].strip()

    # Auditar y verificar el titular con Mistral frente al titular original (sin enviar el cuerpo para ahorrar tokens)
    if title_rw:
        print(f"      - Auditando titular con Mistral frente al original...", flush=True)
        title_rw = verify_headline_with_mistral(original_title=title, rewritten_title=title_rw)
    
    # Dividir el cuerpo en fragmentos que respeten los párrafos
    paragraphs = body.split('\n\n')
    chunks = []
    current_chunk = []
    current_length = 0
    
    for p in paragraphs:
        if not p.strip(): continue
        if current_length + len(p) > 2500 and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [p]
            current_length = len(p)
        else:
            current_chunk.append(p)
            current_length += len(p) + 2
            
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    rewritten_chunks = []
    for i, chunk in enumerate(chunks):
        print(f"      - Reescribiendo fragmento {i+1}/{len(chunks)}...", flush=True)
        rw_chunk = _rewrite_chunk(chunk, "CUERPO", context_title=title_rw or title)
        rewritten_chunks.append(rw_chunk or chunk)
        if len(chunks) > 1: time.sleep(0.5)
        
    final_title = title_rw or title
    final_body = "\n\n".join(rewritten_chunks)
    
    # Capa de seguridad final: sanitizar siempre, incluso si hubo fallback a partes originales
    final_title = fix_grammar_errors(sanitize_media_references(final_title))
    final_body = fix_grammar_errors(sanitize_media_references(final_body))
    
    return final_title, final_body

def _rewrite_chunk(text, type_label, context_title=None):
    keys = [
        os.environ.get("GROQ_REWRITE_2"), os.environ.get("GROQ_REWRITE_3"),
        os.environ.get("GROQ_REWRITE_KEY"), os.environ.get("groq_KEY"), 
        os.environ.get("GROQ_TRANSLATION_KEY"), os.environ.get("GROQ_POLISH_KEY"),
        os.environ.get("GROQ_EUSKERA2"), os.environ.get("GROQ_POLISH2"),
        os.environ.get("GROQ_API_KEY")
    ]
    keys.extend(get_extra_keys())
    valid_keys = [k for k in keys if k]
    if not valid_keys:
        return None

    max_attempts = max(3, len(valid_keys))
    for attempt in range(max_attempts):
        try:
            api_key = get_next_key(valid_keys, "rewrite")
            client = Groq(api_key=api_key)
              
            if type_label == "TÍTULO":
                style_instructions = """1. BREVEDAD CRÍTICA: El titular debe ser directo, impactante y de longitud similar al original (máximo 12-15 palabras).
                2. SÍNTESIS: Capta la esencia de la noticia en una sola frase potente. No des rodeos.
                3. CONJUGACIÓN CORRECTA: Usa siempre verbos conjugados correctamente en castellano de España (por ejemplo: 'se vuelca' y NUNCA 'se volca', 'vuelco' y NUNCA 'volcamiento')."""
            else:
                style_instructions = """1. REESTRUCTURA TOTAL: No te limites a cambiar palabras. Cambia el orden de las ideas y la construcción de las frases. Estilo narrativo propio.
                2. FIDELIDAD ESTRICTA A LOS DATOS: NO ELIMINES NINGÚN DATO RELEVANTE Y NO INVENTES NADA. Si el texto original menciona proyectos específicos, nombres de calles, cifras, listas de medidas o promesas pendientes, DEBEN aparecer íntegramente en la reescritura. Está totalmente prohibido añadir datos, servicios o detalles ficticios.
                3. EXTENSIÓN: El texto reescrito debe tener una longitud similar o superior al original. Está prohibido resumir eliminando detalles técnicos o enumeraciones.
                4. RIQUEZA LÉXICA Y CONJUGACIÓN IMPECABLE: Evita muletillas y usa un lenguaje profesional con conjugaciones correctas en español (por ejemplo: 'se vuelca' en lugar de 'se volca', 'vuelco' en lugar de 'volcamiento', 'se fuerza' en lugar de 'se forza')."""

            system_prompt = f"""Eres un Periodista de Investigación y Redactor Senior experto en la actualidad de Vitoria-Gasteiz.
            Tu tarea es TRANSFORMAR el siguiente {type_label} en una pieza periodística original, evitando el estilo de agencia de noticias.

            INSTRUCCIONES DE ESTILO PARA {type_label}:
            {style_instructions}
            
            REGLAS INNEGOCIABLES Y ESTRICTAS:
            - INTEGRIDAD Y COMPROBACIÓN DE DATOS: Todos los nombres, cifras, fechas, lugares y cargos deben ser 100% EXACTOS y provenir únicamente del texto original.
            - PROHIBIDO INVENTAR O ALUCINAR INFORMACIÓN: No inventes ningún dato, servicio público, aplicación web, mapa interactivo, enlace de descarga o detalle de conveniencia que no se mencione explícitamente en el texto original. Limítate strictly a los hechos narrados.
            - PROHIBIDO RESUMIR: No omitas listas, enumeraciones de proyectos ni detalles técnicos. Si el original es largo, la reescritura debe ser larga.
            - PROHIBIDO utilizar la expresión "en el corazón de Vitoria-Gasteiz" o similares muletillas geográficas repetitivas. Busca alternativas originales.
            - PROHIBIDO mencionar de forma literal los nombres de medios de comunicación de origen (como "Gasteiz Hoy", "El Correo", "Diario de Noticias", "Diario de Noticias de Álava", "Noticias de Álava", "Diario de Álava", etc.). Si el texto original hace referencia a ellos o a sus periodistas, debes sustituir dicha mención por una expresión neutra como "este medio", "el citado diario", "este periódico" o "este canal". Tampoco incluyas frases de autobombo o firmas periodísticas al final del texto.
            - CORRECCIÓN GRAMATICAL: Usa español impecable. Está prohibido usar invenciones o malas conjugaciones como 'se volca', 'se forza', 'se colga', 'se apreta' o 'volcamiento'.
            - CITAS: Si hay declaraciones entre comillas, mantén su esencia o integridad.
            
            REGLA DE FORMATO ABSOLUTA:
            Responde ÚNICAMENTE con el texto transformado.
            NO incluyas introducciones, explicaciones, comentarios, notas al pie, ni etiquetas markdown (como ``` o similares).
            Tu respuesta debe ser de forma directa el texto reescrito."""

            user_content = text
            if context_title and type_label == "CUERPO":
                user_content = f"NOTICIA: {context_title}\n\nTEXTO A REESCRIBIR:\n{text}"

            completion = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}],
                temperature=0.6,
                max_tokens=4000,
                extra_body={"reasoning_effort": "none"}
            )
            
            rewritten = completion.choices[0].message.content.strip()
            
            # Limpiar posibles bloques de razonamiento si los hubiera
            rewritten = clean_thinking_tags(rewritten)
            
            # Si el modelo por error devolvió el texto envuelto en comillas, las quitamos
            if rewritten.startswith('"') and rewritten.endswith('"'):
                rewritten = rewritten[1:-1].strip()
            
            if rewritten and type_label == "CUERPO" and len(rewritten) < len(text) * 0.5:
                print(f"      [RECHAZO LONGITUD] Fragmento reescrito demasiado corto ({len(rewritten)} < {int(len(text)*0.5)}) en intento {attempt+1}", flush=True)
                if attempt < max_attempts - 1: continue

            if rewritten:
                rewritten = sanitize_media_references(rewritten)
                rewritten = fix_grammar_errors(rewritten)

            return rewritten
        except Exception as e:
            if "429" in str(e) or "limit" in str(e).lower():
                if attempt < max_attempts - 1:
                    print(f"      [Rate Limit Groq] Probando siguiente clave de reescritura en rotación...", flush=True)
                    continue
                else:
                    time.sleep(5)
            elif attempt < max_attempts - 1:
                time.sleep(1)
            else:
                print(f"      [ERROR _rewrite_chunk] Todos los intentos fallaron: {e}", flush=True)
            
    return None


def _split_text(text, max_chars):
    # Esta función se mantiene por compatibilidad si se usa en otros sitios, 
    # aunque ahora rewrite_article implementa su propia lógica de párrafos.
    if not text: return []
    chunks = []
    while text:
        if len(text) <= max_chars: chunks.append(text); break
        split_at = text.rfind('\n\n', 0, max_chars)
        if split_at == -1: split_at = text.rfind('\n', 0, max_chars)
        if split_at == -1: split_at = text.rfind('. ', 0, max_chars)
        if split_at == -1: split_at = max_chars
        chunks.append(text[:split_at].strip())
        text = text[split_at:].strip()
    return chunks


def get_extra_keys():
    """Obtiene todas las claves genéricas extras (GROQ_EXTRA1 a GROQ_EXTRA10), soportando varios formatos."""
    extra_keys = []
    for i in range(1, 11):
        val = (
            os.environ.get(f"GROQ_EXTRA{i}") or 
            os.environ.get(f"groq_extra{i}") or 
            os.environ.get(f"GROQ_EXTRA_{i}") or 
            os.environ.get(f"groq_extra_{i}")
        )
        if val and val not in extra_keys:
            extra_keys.append(val)
    return extra_keys


def get_mistral_keys():
    """Obtiene todas las claves de Mistral (MISTRAL_API_KEY, MISTRAL_KEY, MISTRAL1 a MISTRAL10) para rotación."""
    keys = []
    for var in ["MISTRAL_API_KEY", "MISTRAL_KEY", "MISTRAL_TITULARES", "MISTRAL_SECRET"]:
        val = os.environ.get(var)
        if val and val not in keys:
            keys.append(val)
    for i in range(1, 11):
        val = os.environ.get(f"MISTRAL{i}") or os.environ.get(f"mistral{i}")
        if val and val not in keys:
            keys.append(val)
    return keys


def verify_headline_with_mistral(original_title, rewritten_title):
    """
    Verifica con Mistral que el titular reescrito guarde estricta fidelidad con el titular original
    y que sea totalmente correcto a nivel gramatical en castellano.
    Compara ÚNICAMENTE el titular original y el reescrito para minimizar consumo de tokens.
    """
    mistral_keys = get_mistral_keys()
    if not mistral_keys:
        return fix_grammar_errors(sanitize_media_references(rewritten_title))

    system_prompt = """Eres un Editor Jefe Periodístico especializado en veracidad e integridad informativa.
Tu tarea es auditar y verificar un TITULAR REESCRITO comparándolo con el TITULAR ORIGINAL de la fuente.

REGLAS DE AUDITORÍA:
1. FIDELIDAD TEMÁTICA STRICTA: El titular reescrito debe tratar EXACTAMENTE del mismo suceso, noticia o hecho que el titular original. Si el titular reescrito inventa datos, habla de un tema diferente o cambia el significado de la noticia, ES UN RECHAZO por alucinación. En ese caso, debes proponer una adaptación fiel del titular original.
2. CORRECCIÓN GRAMATICAL: El titular debe ser gramaticalmente perfecto en castellano de España (ej: 'se vuelca' y NUNCA 'se volca', 'vuelco' y NUNCA 'volcamiento', 'se fuerza' y NUNCA 'se forza').
3. SÍNTESIS: Mantén un tono directo y profesional (máximo 12-15 palabras).

Formato de respuesta JSON obligatorio:
{
  "is_faithful": true/false,
  "final_title": "El titular verificado, fiel y correcto"
}"""

    user_content = f"TITULAR ORIGINAL (Fuente):\n{original_title}\n\nTITULAR REESCRITO A AUDITAR:\n{rewritten_title}"

    max_attempts = max(3, len(mistral_keys))
    for attempt in range(max_attempts):
        try:
            api_key = get_next_key(mistral_keys, "mistral_headline")
            client = Mistral(api_key=api_key)

            response = client.chat.complete(
                model="mistral-small-latest",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            raw_text = clean_thinking_tags(response.choices[0].message.content)
            data = json.loads(raw_text)

            final_title = data.get("final_title") or (rewritten_title if data.get("is_faithful") else original_title)
            final_title = final_title.strip()
            if final_title.startswith('"') and final_title.endswith('"'):
                final_title = final_title[1:-1].strip()

            final_title = fix_grammar_errors(sanitize_media_references(final_title))

            if not data.get("is_faithful", True):
                print(f"      [Mistral ALERTA] Alucinación detectada en titular. Corregido a: '{final_title}'", flush=True)
            else:
                print(f"      [Mistral OK] Titular auditado y verificado correctamente.", flush=True)

            return final_title

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "rate" in error_str.lower() or "limit" in error_str.lower():
                if attempt < max_attempts - 1:
                    print(f"      [Mistral Rate Limit] Probando siguiente clave en rotación...", flush=True)
                    continue
                else:
                    time.sleep(5)
            elif attempt < max_attempts - 1:
                time.sleep(1)
            else:
                print(f"      [Mistral FAIL Auditoría Titular]: {e}", flush=True)

    return fix_grammar_errors(sanitize_media_references(rewritten_title))


def verify_translation_with_mistral(original_text, translated_text, target_lang, type_label):
    """Verifica y corrige una traducción usando Mistral como segundo modelo.
    
    Recibe el texto original (ES) y la traducción de Groq, y devuelve
    la traducción corregida o la misma si era correcta.
    """
    mistral_keys = get_mistral_keys()
    if not mistral_keys:
        print("      [Mistral] No hay keys configuradas, se omite verificación.", flush=True)
        return translated_text
    
    # Nombres de idioma para el prompt
    lang_names = {
        "eu": "Basque (euskara batua)",
        "pl": "Polish (język polski)",
        "fr": "French (français)",
        "en": "English"
    }
    lang_name = lang_names.get(target_lang, target_lang)
    type_desc = "title" if type_label == "TÍTULO" else "body"
    
    # Instrucciones especiales para euskera
    extra_rules = ""
    if target_lang == "eu":
        extra_rules = "\n- In Basque, 'Vitoria' alone MUST be 'Gasteiz'. Keep 'Vitoria-Gasteiz' unchanged."
    
    system_prompt = f"""You are a professional translation reviewer and copyeditor. Your job is to verify, polish, and correct a Spanish-to-{lang_name} translation of a news article {type_desc}.

Rules:
- Compare the ORIGINAL Spanish text with the TRANSLATION provided.
- Check for and correct any grammatical errors, spelling mistakes, punctuation issues, or mistranslations.
- Check for and correct robotic or overly literal phrasing. Ensure the text flows naturally and sounds like it was written directly by a native speaker of {lang_name} while keeping the original meaning.
- Enhance the style to match that of a professional news report.
- If the translation is already fully accurate, natural, and stylistically correct, return it EXACTLY as-is.
- Respond ONLY with the final verified/corrected {lang_name} text. No explanations, no comments, no markup.
- Keep proper names, numbers, places, streets, and dates intact.{extra_rules}"""

    user_content = f"ORIGINAL (Spanish):\n{original_text}\n\nTRANSLATION ({lang_name}):\n{translated_text}"
    
    max_attempts = max(3, len(mistral_keys))
    for attempt in range(max_attempts):
        try:
            api_key = get_next_key(mistral_keys, "mistral")
            client = Mistral(api_key=api_key)
            
            response = client.chat.complete(
                model="mistral-small-latest",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.1
            )
            
            verified = response.choices[0].message.content.strip()
            if verified:
                # Limpiar comillas innecesarias
                if verified.startswith('"') and verified.endswith('"'):
                    verified = verified[1:-1].strip()
                print(f"      [Mistral OK] Verificacion completada.", flush=True)
                return verified
                
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "rate" in error_str.lower() or "limit" in error_str.lower():
                if attempt < max_attempts - 1:
                    print(f"      [Mistral Rate Limit] Probando siguiente clave Mistral en rotación...", flush=True)
                    continue
                else:
                    time.sleep(5)
            elif attempt < max_attempts - 1:
                time.sleep(1)
            else:
                print(f"      [Mistral FAIL] Error verificando ({type_label}): {e}", flush=True)
    
    # Si falla Mistral, devolvemos la traducción de Groq sin modificar
    print(f"      [Mistral FAIL] No se pudo verificar, se usa traduccion de Groq.", flush=True)
    return translated_text


def get_translation_keys(target_lang):
    """Obtiene todas las claves de API de Groq configuradas para un idioma específico."""
    prefixes = {
        "eu": "TRADUCCION_EUSKARA",
        "pl": "TRADUCCION_POLACO",
        "fr": "TRADUCCION_FRANCAIS",
        "en": "TRADUCCION_ENGLISH"
    }
    
    prefix = prefixes.get(target_lang)
    if not prefix:
        return []
        
    keys = []
    
    # 1. Intentar obtener clave base (sin número al final, ej. TRADUCCION_FRANCAIS)
    base_key = os.environ.get(prefix)
    if base_key:
        keys.append(base_key)
        
    # 2. Intentar obtener claves numeradas (ej. TRADUCCION_FRANCAIS1, TRADUCCION_FRANCAIS2, etc. hasta el 10)
    for i in range(1, 11):
        key_name = f"{prefix}{i}"
        key_val = os.environ.get(key_name)
        if key_val and key_val not in keys:
            keys.append(key_val)
            
    # 3. Mezclar las claves genéricas extras como fallback
    for extra_key in get_extra_keys():
        if extra_key not in keys:
            keys.append(extra_key)
            
    return keys


def replace_vitoria_basque(text):
    """Reemplaza Vitoria y sus declinaciones en euskera por Gasteiz y sus declinaciones correctas,
    protegiendo 'Vitoria-Gasteiz' de ser alterado."""
    if not text:
        return text
        
    # Proteger temporalmente Vitoria-Gasteiz (incluidas declinaciones)
    def protect(m):
        return m.group(0).replace("Vitoria-Gasteiz", "___VG___").replace("Vitoria - Gasteiz", "___VG_SPACE___")
        
    text_temp = re.sub(r'\bVitoria\s*-\s*Gasteiz[a-zA-Z]*\b', protect, text, flags=re.IGNORECASE)
    
    declensions = [
        (r'\bVitoriakoak\b', 'Gasteizkoak'),
        (r'\bVitoriakoari\b', 'Gasteizkoari'),
        (r'\bVitoriakoei\b', 'Gasteizkoei'),
        (r'\bVitoriakoa\b', 'Gasteizkoa'),
        (r'\bVitoriako\b', 'Gasteizko'),
        (r'\bVitoriak\b', 'Gasteizek'),
        (r'\bVitorian\b', 'Gasteizen'),
        (r'\bVitoriara\b', 'Gasteizera'),
        (r'\bVitoriatik\b', 'Gasteiztik'),
        (r'\bVitoriari\b', 'Gasteizi'),
        (r'\bVitoriarrak\b', 'Gasteiztarrak'),
        (r'\bVitoriarra\b', 'Gasteiztarra'),
        (r'\bVitoriar\b', 'Gasteiztar'),
        (r'\bVitoria\b', 'Gasteiz')
    ]
    
    for pattern, repl in declensions:
        def case_repl(match):
            m = match.group(0)
            if m[0].isupper():
                return repl
            return repl.lower()
        text_temp = re.sub(pattern, case_repl, text_temp, flags=re.IGNORECASE)
        
    # Restaurar
    text_temp = text_temp.replace("___VG___", "Vitoria-Gasteiz").replace("___VG_SPACE___", "Vitoria - Gasteiz")
    return text_temp


def translate_text(text, target_lang, type_label, context_title=None):
    """Traduce un fragmento de texto al euskera ('eu'), polaco ('pl'), francés ('fr') o inglés ('en') usando las llaves dedicadas."""
    max_retries = 3
    model_name = "qwen/qwen3.6-27b"
    
    if target_lang == "eu":
        lang_name = "Basque (euskara batua)"
        pair_desc = "Spanish-Basque"
        title_context_label = "BASQUE TITLE CONTEXT"
    elif target_lang == "pl":
        lang_name = "Polish (język polski)"
        pair_desc = "Spanish-Polish"
        title_context_label = "POLISH TITLE CONTEXT"
    elif target_lang == "fr":
        lang_name = "French (français)"
        pair_desc = "Spanish-French"
        title_context_label = "FRENCH TITLE CONTEXT"
    elif target_lang == "en":
        lang_name = "English (English)"
        pair_desc = "Spanish-English"
        title_context_label = "ENGLISH TITLE CONTEXT"
    else:
        print(f"Error: Idioma destino '{target_lang}' no soportado.", flush=True)
        return None
        
    valid_keys = get_translation_keys(target_lang)
    if not valid_keys:
        print(f"Error: No se han configurado las llaves para '{target_lang}' en el .env", flush=True)
        return None


    type_desc_en = "title" if type_label == "TÍTULO" else "body"

    max_attempts = max(3, len(valid_keys))
    for attempt in range(max_attempts):
        try:
            api_key = get_next_key(valid_keys, f"trans_{target_lang}")
            client = Groq(api_key=api_key)
            extra_instructions = ""
            if target_lang == "eu":
                extra_instructions = "\n5. CRITICAL: In Basque, the city name 'Vitoria' MUST ALWAYS be translated as 'Gasteiz'. If the text says 'Vitoria-Gasteiz', keep it as 'Vitoria-Gasteiz'. But if it says only 'Vitoria', translate it to 'Gasteiz'."

            system_prompt = f"""You are a professional bilingual translator specializing in {pair_desc} translation. Your task is to translate the {type_desc_en} of a news article from Spanish to {lang_name} with absolute precision and naturalness.

CRITICAL INSTRUCTIONS:
1. Respond ONLY with the translated text in {lang_name}.
2. DO NOT add any introductions, explanations, comments, or personal notes.
3. Keep proper names, exact numbers, places, streets, and dates intact.
4. Ensure the output is natural and fluent.{extra_instructions}"""

            user_content = text
            if context_title and type_label == "CUERPO":
                user_content = f"{title_context_label}: {context_title}\n\nSPANISH TEXT TO TRANSLATE:\n{text}"

            completion = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}],
                temperature=0.2,
                extra_body={"reasoning_effort": "none"}
            )
            
            translated = completion.choices[0].message.content.strip()
            if translated:
                # Limpiar bloques de razonamiento <think>...</think> (defensa extra)
                translated = clean_thinking_tags(translated)
                # Quitar comillas innecesarias
                if translated.startswith('"') and translated.endswith('"'):
                    translated = translated[1:-1].strip()
                # Regla de euskera para Vitoria -> Gasteiz
                if target_lang == "eu":
                    translated = replace_vitoria_basque(translated)
                # Verificar la traducción con Mistral
                translated = verify_translation_with_mistral(
                    text, translated, target_lang, type_label
                )
                # Re-aplicar regla euskera tras verificación de Mistral
                if target_lang == "eu":
                    translated = replace_vitoria_basque(translated)
                return translated
        except Exception as e:
            if "429" in str(e) or "limit" in str(e).lower():
                if attempt < max_attempts - 1:
                    print(f"      [Rate Limit Groq] Probando siguiente clave de traducción ({target_lang}) en rotación...", flush=True)
                    continue
                else:
                    sleep_time = 10
                    print(f"      [Rate Limit Groq] Todas las claves agotadas, esperando {sleep_time}s...", flush=True)
                    time.sleep(sleep_time)
            elif attempt < max_attempts - 1:
                time.sleep(1)
            else:
                print(f"Error al traducir a {target_lang} ({type_label}) con Groq ({model_name}): {e}", flush=True)
                
    return None


def translate_to_euskera(text, type_label, context_title=None):
    return translate_text(text, "eu", type_label, context_title)


def translate_to_polish(text, type_label, context_title=None):
    return translate_text(text, "pl", type_label, context_title)


def translate_to_french(text, type_label, context_title=None):
    return translate_text(text, "fr", type_label, context_title)


def translate_to_english(text, type_label, context_title=None):
    return translate_text(text, "en", type_label, context_title)


def translate_article(title, body, target_lang="eu"):
    """Traduce el artículo completo (título y cuerpo por fragmentos) al idioma destino."""
    lang_labels = {"eu": "euskera", "pl": "polaco", "fr": "francés", "en": "inglés"}
    lang_label = lang_labels.get(target_lang, target_lang)
    print(f"    - Iniciando traducción al {lang_label}...", flush=True)
    title_tr = translate_text(title, target_lang, "TÍTULO")
    
    if not title_tr:
        title_tr = title
        
    paragraphs = body.split('\n\n')
    chunks = []
    current_chunk = []
    current_length = 0
    
    for p in paragraphs:
        if not p.strip(): continue
        if current_length + len(p) > 2500 and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [p]
            current_length = len(p)
        else:
            current_chunk.append(p)
            current_length += len(p) + 2
            
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    translated_chunks = []
    for i, chunk in enumerate(chunks):
        print(f"      - Traduciendo fragmento {i+1}/{len(chunks)}...", flush=True)
        tr_chunk = translate_text(chunk, target_lang, "CUERPO", context_title=title_tr)
        translated_chunks.append(tr_chunk or chunk)
        # Delay de cortesía entre fragmentos; el retry gestiona rate limits reales
        time.sleep(0.5)
            
    return title_tr, "\n\n".join(translated_chunks)


