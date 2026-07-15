import re
import os
import json
import random
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
    'relevo', 'continuidad', 'tradición', 'familia', 'futuro', 'crean', 'vuelve', 'abre', 'abren',
    'fiesta', 'fiestas', 'música', 'celebración', 'celebraciones', 'concierto', 'conciertos', 
    'diversión', 'danza', 'baile', 'deporte', 'deportes', 'gastronomía', 'popular'
}

PALABRAS_NEGATIVAS = {
    'malo', 'mala', 'peor', 'negativo', 'fracaso', 'error', 'problema', 'crisis', 'daño', 
    'muerte', 'fallece', 'accidente', 'robo', 'robos', 'robar', 'robado', 'robada', 'robados', 'robadas',
    'detenido', 'detenidos', 'detenida', 'detenidas', 'agresión', 'agresiones', 'pelea', 'peleas',
    'herido', 'herida', 'heridos', 'heridas', 'lesionado', 'lesionada', 'lesionados', 'lesionadas',
    'asesinato', 'asesinado', 'asesinada', 'asesinados', 'asesinadas', 'matar', 'apuñalado', 'apuñalada', 'apuñalar',
    'denuncia', 'denuncias', 'corte', 'huelga', 'huelgas', 'protesta', 'incendio', 'atropello', 'crimen', 'estafa',
    'pérdida', 'caída', 'baja', 'tensión', 'riesgo', 'peligro', 'inseguro', 'sucio', 'abandono',
    'cierre', 'cierran', 'despido', 'despidos', 'semana santa', 'procesión', 'religión', 'iglesia', 
    'culto', 'cura', 'obispo', 'religioso', 'religiosa', 'religiosas', 'religiosos', 'convento', 'conventos',
    'clarisa', 'clarisas', 'papa', 'vaticano', 'misa', 'católico', 
    'cofradía', 'peregrinación','PP', 'VOX', 'peregrinar', 'diócesis', 'paralisis', 'parálisis',
    'rechazo', 'rechazos', 'oposición', 'oposicion', 'enfrentamiento', 'enfrentamientos',
    'guardia civil', 'guardias civiles', 'guardia zibila', 'guardia zibilak'
}

NEGACIONES = {'no', 'ni', 'nunca', 'tampoco', 'sin'}

def clean_thinking_tags(text):
    """Elimina bloques <think>...</think> que genera Qwen en modo thinking.
    Maneja tanto el caso normal (<think>...</think>) como el truncado (<think>... sin cierre)."""
    if not text:
        return text
    return re.sub(r'<think>[\s\S]*?(?:</think>|$)', '', text).strip()

def heuristic_fallback(text):
    if not text: return 'neutral', 0.0, 'Sociedad'
    text_lower = text.lower()
    
    # REGLAS ESPECIALES (usando regex para evitar falsos positivos como "curarse")
    if 'banco de alimentos' in text_lower or re.search(r'\b(guardias?\s+civil(?:es)?|guardia\s+zibila?k?|iglesia|cura|curas|obispo|obispos|religioso|religiosos|religiosas?|conventos?|clarisas?|peregrinación|peregrinar|diócesis|semana santa|tensión pol[íi]tica)\b', text_lower):
        return 'negativa', -0.8, 'Sociedad'
    
    words = re.findall(r'\w+', text_lower)

    pos_count = 0; neg_count = 0
    for i, word in enumerate(words):
        if word in PALABRAS_POSITIVAS:
            if i > 0 and words[i-1] in NEGACIONES: neg_count += 1
            else: pos_count += 1
        elif word in PALABRAS_NEGATIVAS:
            if i > 0 and words[i-1] in NEGACIONES: pos_count += 1
            else: neg_count += 1
    total = pos_count + neg_count
    # Si la densidad de coincidencias es muy baja (1 o menos), preferimos delegar a la IA
    if total <= 1: return 'neutral', 0.0, 'Sociedad'
    score = (pos_count - neg_count) / total
    if score > 0.05: return 'positiva', score, 'Sociedad'
    elif score < -0.05: return 'negativa', score, 'Sociedad'
    else: return 'neutral', score, 'Sociedad'
 
def analyze_sentiment(text):
    """Analiza sentimiento y categoría. Primero pasa por el modelo heurístico y, si es neutral, pasa por la IA."""
    # 1. Pasar primero por el modelo heurístico
    heur_sentiment, heur_score, heur_category = heuristic_fallback(text)
    if heur_sentiment in ('positiva', 'negativa'):
        return heur_sentiment, heur_score, heur_category
        
    # 2. Si es neutral, recurrir a la IA (Groq)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Pool de llaves actualizado
            keys = [
                os.environ.get("GROQ_REWRITE_2"), os.environ.get("GROQ_REWRITE_3"),
                os.environ.get("GROQ_REWRITE_KEY"), os.environ.get("groq_KEY"), 
                os.environ.get("GROQ_TRANSLATION_KEY"), os.environ.get("GROQ_POLISH_KEY"),
                os.environ.get("GROQ_EUSKERA2"), os.environ.get("GROQ_POLISH2"),
                os.environ.get("GROQ_API_KEY")
            ]
            valid_keys = [k for k in keys if k]
            if not valid_keys:
                return heur_sentiment, heur_score, heur_category
                
            api_key = random.choice(valid_keys)
            
            client = Groq(api_key=api_key)
            system_prompt = """Eres un clasificador experto de noticias de Vitoria-Gasteiz.
            Responde ÚNICAMENTE en JSON: {"sentiment": "positiva/negativa/neutral", "score": -1.0 a 1.0, "category": "Política/Economía/Sociedad/Deportes/Cultura/Sucesos/Urbanismo"}
            REGLA ESPECIAL: Cualquier noticia que mencione a la "Guardia Civil", "Iglesia", "Curas", "Obispos", "Diócesis", "Peregrinación", "Convento", "Religiosas", "Clarisas", "Banco de Alimentos" o temas religiosos debe ser clasificada siempre como "negativa" con un score de -0.8."""
            
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
                print(f"Error clasificando con Groq: {e}. Usando el resultado heurístico original.")
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
    final_title = sanitize_media_references(final_title)
    final_body = sanitize_media_references(final_body)
    
    return final_title, final_body

def _rewrite_chunk(text, type_label, context_title=None):
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
            valid_keys = [k for k in keys if k]
            api_key = random.choice(valid_keys)
            client = Groq(api_key=api_key)
              
            if type_label == "TÍTULO":
                style_instructions = """1. BREVEDAD CRÍTICA: El titular debe ser directo, impactante y de longitud similar al original (máximo 12-15 palabras).
                2. SÍNTESIS: Capta la esencia de la noticia en una sola frase potente. No des rodeos."""
            else:
                style_instructions = """1. REESTRUCTURA TOTAL: No te limites a cambiar palabras. Cambia el orden de las ideas y la construcción de las frases. Estilo narrativo propio.
                2. FIDELIDAD ESTRICTA A LOS DATOS: NO ELIMINES NINGÚN DATO RELEVANTE Y NO INVENTES NADA. Si el texto original menciona proyectos específicos, nombres de calles, cifras, listas de medidas o promesas pendientes, DEBEN aparecer íntegramente en la reescritura. Está totalmente prohibido añadir datos, servicios o detalles ficticios.
                3. EXTENSIÓN: El texto reescrito debe tener una longitud similar o superior al original. Está prohibido resumir eliminando detalles técnicos o enumeraciones.
                4. RIQUEZA LÉXICA: Evita muletillas y usa un lenguaje profesional y evocador."""

            system_prompt = f"""Eres un Periodista de Investigación y Redactor Senior experto en la actualidad de Vitoria-Gasteiz.
            Tu tarea es TRANSFORMAR el siguiente {type_label} en una pieza periodística original, evitando el estilo de agencia de noticias.

            INSTRUCCIONES DE ESTILO PARA {type_label}:
            {style_instructions}
            
            REGLAS INNEGOCIABLES Y ESTRICTAS:
            - INTEGRIDAD Y COMPROBACIÓN DE DATOS: Todos los nombres, cifras, fechas, lugares y cargos deben ser 100% EXACTOS y provenir únicamente del texto original.
            - PROHIBIDO INVENTAR O ALUCINAR INFORMACIÓN: No inventes ningún dato, servicio público, aplicación web, mapa interactivo, enlace de descarga o detalle de conveniencia que no se mencione explícitamente en el texto original. Limítate estrictamente a los hechos narrados.
            - PROHIBIDO RESUMIR: No omitas listas, enumeraciones de proyectos ni detalles técnicos. Si el original es largo, la reescritura debe ser larga.
            - PROHIBIDO utilizar la expresión "en el corazón de Vitoria-Gasteiz" o similares muletillas geográficas repetitivas. Busca alternativas originales.
            - PROHIBIDO mencionar de forma literal los nombres de medios de comunicación de origen (como "Gasteiz Hoy", "El Correo", "Diario de Noticias", "Diario de Noticias de Álava", "Noticias de Álava", "Diario de Álava", etc.). Si el texto original hace referencia a ellos o a sus periodistas, debes sustituir dicha mención por una expresión neutra como "este medio", "el citado diario", "este periódico" o "este canal". Tampoco incluyas frases de autobombo o firmas periodísticas al final del texto.
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
                if attempt < max_retries - 1: continue

            if rewritten:
                rewritten = sanitize_media_references(rewritten)

            return rewritten
        except Exception as e:
            print(f"      [ERROR _rewrite_chunk] Intento {attempt+1} falló: {e}", flush=True)
            if attempt < max_retries - 1: time.sleep(1)
            
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


def translate_text(text, target_lang, type_label, context_title=None):
    """Traduce un fragmento de texto al euskera ('eu') o polaco ('pl') usando las llaves dedicadas."""
    max_retries = 3
    model_name = "qwen/qwen3.6-27b"
    
    if target_lang == "eu":
        keys = [
            os.environ.get("TRADUCCION_EUSKARA1"),
            os.environ.get("TRADUCCION_EUSKARA2")
        ]
        lang_name = "Basque (euskara batua)"
        pair_desc = "Spanish-Basque"
        title_context_label = "BASQUE TITLE CONTEXT"
    elif target_lang == "pl":
        keys = [
            os.environ.get("TRADUCCION_POLACO1"),
            os.environ.get("TRADUCCION_POLACO2")
        ]
        lang_name = "Polish (język polski)"
        pair_desc = "Spanish-Polish"
        title_context_label = "POLISH TITLE CONTEXT"
    else:
        print(f"Error: Idioma destino '{target_lang}' no soportado.", flush=True)
        return None
        
    valid_keys = [k for k in keys if k]
    if not valid_keys:
        print(f"Error: No se han configurado las llaves para '{target_lang}' en el .env", flush=True)
        return None

    type_desc_en = "title" if type_label == "TÍTULO" else "body"

    for attempt in range(max_retries):
        try:
            api_key = random.choice(valid_keys)
            client = Groq(api_key=api_key)
            
            system_prompt = f"""You are a professional bilingual translator specializing in {pair_desc} translation. Your task is to translate the {type_desc_en} of a news article from Spanish to {lang_name} with absolute precision and naturalness.

CRITICAL INSTRUCTIONS:
1. Respond ONLY with the translated text in {lang_name}.
2. DO NOT add any introductions, explanations, comments, or personal notes.
3. Keep proper names, exact numbers, places, streets, and dates intact.
4. Ensure the output is natural and fluent."""

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
                return translated
        except Exception as e:
            if "429" in str(e) or "limit" in str(e).lower():
                sleep_time = 15 if attempt == 0 else 30
                print(f"      [Rate Limit Groq] Esperando {sleep_time}s para liberar TPM...", flush=True)
                time.sleep(sleep_time)
            elif attempt < max_retries - 1:
                time.sleep(2)
            else:
                print(f"Error al traducir a {target_lang} ({type_label}) con Groq ({model_name}): {e}", flush=True)
                
    return None


def translate_to_euskera(text, type_label, context_title=None):
    return translate_text(text, "eu", type_label, context_title)


def translate_to_polish(text, type_label, context_title=None):
    return translate_text(text, "pl", type_label, context_title)


def translate_article(title, body, target_lang="eu"):
    """Traduce el artículo completo (título y cuerpo por fragmentos) al idioma destino."""
    lang_label = "euskera" if target_lang == "eu" else "polaco"
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
        # Delay preventivo entre fragmentos para proteger la cuota TPM de 8000
        time.sleep(1.5)
            
    return title_tr, "\n\n".join(translated_chunks)


