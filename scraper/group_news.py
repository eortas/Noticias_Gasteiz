import os
import json
import time
import random
import re
import urllib.parse
from collections import defaultdict
from groq import Groq
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def clean_thinking_tags(text):
    """Elimina bloques <think>...</think> que genera Qwen en modo thinking."""
    if not text:
        return text
    return re.sub(r'<think>[\s\S]*?(?:</think>|$)', '', text).strip()

# Lista ampliada de stopwords en español para evitar falsos positivos
SPANISH_STOPWORDS = {
    # Pronombres y artículos
    'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'este', 'esta', 'estos', 'estas', 'ese', 'esa', 'esos', 'esas',
    'aquel', 'aquella', 'aquellos', 'aquellas', 'mi', 'mis', 'tu', 'tus', 'su', 'sus', 'nuestro', 'nuestra', 'nuestros', 'nuestras',
    'vuestro', 'vuestra', 'vuestros', 'vuestras', 'yo', 'tú', 'él', 'ella', 'nosotros', 'nosotras', 'vosotros', 'vosotras', 'ellos', 'ellas',
    'me', 'te', 'se', 'nos', 'os', 'le', 'les', 'lo', 'la', 'los', 'las', 'mí', 'ti', 'sí', 'conmigo', 'contigo', 'consigo',
    # Preposiciones
    'a', 'ante', 'bajo', 'cabe', 'con', 'contra', 'de', 'desde', 'durante', 'en', 'entre', 'hacia', 'hasta', 'mediante', 'para',
    'por', 'según', 'sin', 'so', 'sobre', 'tras', 'versus', 'vía', 'al', 'del',
    # Conjunciones
    'y', 'e', 'ni', 'o', 'u', 'pero', 'mas', 'sino', 'aunque', 'porque', 'pues', 'como', 'siquiera',
    # Verbos comunes y auxiliares
    'ser', 'soy', 'eres', 'es', 'somos', 'sois', 'son', 'fui', 'fuiste', 'fue', 'fuimos', 'fuisteis', 'fueron',
    'era', 'eras', 'éramos', 'erais', 'eran', 'seré', 'serás', 'será', 'seremos', 'seréis', 'serán',
    'sea', 'seas', 'seamos', 'seáis', 'sean', 'sido', 'siendo',
    'estar', 'estoy', 'estás', 'está', 'estamos', 'estáis', 'están', 'estuve', 'estuviste', 'estuvo', 'estuvimos', 'estuvisteis', 'estuvieron',
    'estaba', 'estabas', 'estábamos', 'estabais', 'estaban', 'estaré', 'estarás', 'estará', 'estaremos', 'estaréis', 'estarán',
    'esté', 'estés', 'estemos', 'estéis', 'estén', 'estado', 'estando',
    'haber', 'he', 'has', 'ha', 'hemos', 'habéis', 'han', 'había', 'habías', 'habíamos', 'habíais', 'habían',
    'haya', 'hayas', 'hayamos', 'hayáis', 'hayan', 'hubo', 'hubieron', 'hubiera', 'hubieras', 'hubiéramos', 'hubierais', 'hubieran',
    'tener', 'tengo', 'tienes', 'tiene', 'tenemos', 'tenéis', 'tienen', 'tenía', 'tenías', 'teníamos', 'teníais', 'tenían',
    'tenga', 'tengas', 'tengamos', 'tengáis', 'tengan', 'tuvo', 'tuvieron', 'tuviera', 'tuvieras', 'tuviéramos', 'tuvierais', 'tuvieran',
    'hacer', 'hago', 'haces', 'hace', 'hacemos', 'hacéis', 'hacen', 'hacía', 'hacías', 'hacíamos', 'hacíais', 'hacían',
    'haga', 'hagas', 'hagamos', 'hagáis', 'hagan', 'hizo', 'hicieron', 'hiciera', 'hicieras', 'hiciéramos', 'hicierais', 'hicieran',
    'hecho', 'haciendo',
    'poder', 'puedo', 'puedes', 'puede', 'podemos', 'podéis', 'pueden', 'podía', 'podías', 'podíamos', 'podíais', 'podían',
    'pueda', 'puedas', 'puedamos', 'puedáis', 'puedan', 'pudo', 'pudieron', 'pudiera', 'pudieras', 'pudiéramos', 'pudierais', 'pudieran',
    'decir', 'digo', 'dices', 'dice', 'decimos', 'decís', 'dicen', 'dije', 'dijiste', 'dijo', 'dijimos', 'dijisteis', 'dijeron',
    'diga', 'digas', 'digamos', 'digáis', 'digan', 'dicho', 'diciendo',
    'ir', 'voy', 'vas', 'va', 'vamos', 'vais', 'van', 'iba', 'ibas', 'íbamos', 'ibais', 'iban',
    'vaya', 'vayas', 'vayamos', 'vayáis', 'vayan',
    # Adverbios y otros cuantificadores
    'muy', 'más', 'menos', 'tan', 'tanto', 'así', 'cómo', 'cuándo', 'cuando', 'dónde', 'donde', 'quién', 'quien',
    'qué', 'que', 'ya', 'todavía', 'aún', 'ahora', 'después', 'antes', 'bien', 'mal', 'tal', 'tales',
    'mismo', 'misma', 'mismos', 'mismas', 'otro', 'otra', 'otros', 'otras', 'ambos', 'ambas', 'cada', 'alguno', 'alguna',
    'algunos', 'algunas', 'ninguno', 'ninguna', 'ningunos', 'ningunas', 'todo', 'toda', 'todos', 'todas', 'mucho', 'mucha',
    'muchos', 'muchas', 'poco', 'poca', 'pocos', 'pocas', 'varios', 'varias', 'solo', 'sólo',
    # Términos específicos de sitios/noticias locales
    'correo', 'gasteiz', 'hoy', 'noticias', 'alava', 'vitoria', 'diario', 'araba', 'html', 'htm'
}

def clean_accents(s):
    """Elimina tildes y diéresis para asegurar coincidencia robusta de caracteres."""
    if not s:
        return ""
    replacements = (
        ("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"),
        ("ü", "u"), ("ñ", "n"), ("Á", "A"), ("É", "E"), ("Í", "I"),
        ("Ó", "O"), ("Ú", "U"), ("Ü", "U"), ("Ñ", "N")
    )
    for a, b in replacements:
        s = s.replace(a, b)
    return s

# Pre-calcular stopwords normalizadas para eficiencia
CLEANED_STOPWORDS = {clean_accents(w.lower()) for w in SPANISH_STOPWORDS}

def tokenize(text):
    """Tokeniza un texto eliminando palabras vacías y caracteres especiales (igual que en app.js)."""
    if not text:
        return set()
    text = clean_accents(text.lower())
    text = re.sub(r'[.,\/#!$%\^&\*;:{}=\-_`~()?"\'\n\r0-9]', ' ', text)
    words = text.split()
    return {w for w in words if len(w) > 2 and w not in CLEANED_STOPWORDS}

def jaccard_similarity(set_a, set_b):
    """Calcula el índice de similitud de Jaccard entre dos conjuntos."""
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)

def extract_key_entities(text):
    """Extrae entidades clave (nombres propios, siglas) del texto original (antes de lowercase)."""
    if not text:
        return set()
    # Limpiar caracteres especiales pero mantener mayúsculas
    clean = re.sub(r'[.,\/#!$%\^&\*;:{}=\-_`~()?"\'\n\r0-9]', ' ', text)
    words = clean.split()
    entities = set()
    for w in words:
        if len(w) < 2:
            continue
        w_norm = clean_accents(w.lower())
        if w_norm in CLEANED_STOPWORDS:
            continue
        if w[0].isupper() or w.isupper():
            entities.add(w_norm)
    return entities

def overlap_score(set_a, set_b):
    """Calcula la proporción de tokens compartidos sobre el menor de los dos conjuntos.
    Más generoso que Jaccard cuando un artículo es mucho más largo que otro."""
    if not set_a or not set_b:
        return 0.0
    shared = len(set_a & set_b)
    min_size = min(len(set_a), len(set_b))
    return shared / min_size if min_size > 0 else 0.0

def get_groq_client():
    """Selecciona una clave de Groq disponible y devuelve un cliente inicializado."""
    keys = [
        os.environ.get("DEDUPLICITY1"),
        os.environ.get("DEDUPLICITY2"),
        os.environ.get("GROQ_REWRITE_2"),
        os.environ.get("GROQ_REWRITE_3"),
        os.environ.get("GROQ_REWRITE_KEY"),
        os.environ.get("groq_KEY"),
        os.environ.get("GROQ_TRANSLATION_KEY"),
        os.environ.get("GROQ_POLISH_KEY"),
        os.environ.get("GROQ_EUSKERA2"),
        os.environ.get("GROQ_POLISH2"),
        os.environ.get("GROQ_API_KEY")
    ]
    valid_keys = [k for k in keys if k]
    if not valid_keys:
        return None
    
    # Selecciona una clave aleatoriamente del pool
    api_key = random.choice(valid_keys)
    return Groq(api_key=api_key)

def verify_group_with_llm(group):
    """Envía el grupo de noticias sospechosas al LLM para validar si son la misma historia."""
    client = get_groq_client()
    if not client:
        print("    [AVISO] No hay claves de Groq disponibles. Se saltará la verificación por IA.")
        return None

    # Preparar el contenido del prompt con los detalles de las noticias
    content = "Analiza estas noticias locales y dinos cuáles describen EXACTAMENTE el mismo suceso:\n\n"
    for item in group:
        content += f"ID: {item['id']}\n"
        content += f"Título: {item.get('title', '')}\n"
        content += f"Fuente: {item.get('source', '')}\n"
        content += f"Fecha: {item.get('date', '')}\n"
        content += f"Cuerpo: {item.get('body', '')[:350]}\n"
        content += "---------------------------------\n"

    system_prompt = """Eres un periodista y clasificador de noticias profesional. Tu tarea es analizar un grupo de noticias y determinar si describen EXACTAMENTE el mismo suceso (por ejemplo, el mismo accidente, el mismo robo, el mismo detenido, la misma rueda de prensa) o si son sucesos diferentes (por ejemplo, dos robos distintos en zonas distintas, detenciones de distintas personas, etc.).

Agrupa los IDs de las noticias que corresponden al mismo suceso.
Si todas pertenecen al mismo suceso, devuélvelas en un único grupo.
Si hay noticias de sucesos distintos, sepáralas en grupos diferentes.

Devuelve la respuesta estrictamente en formato JSON con el siguiente esquema exacto:
{
  "subgroups": [
    ["id1", "id2"],
    ["id3"]
  ]
}
No devuelvas ninguna otra explicación, ni bloques de código markdown, solo el JSON puro."""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            completion = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
                extra_body={"reasoning_effort": "none"}
            )
            
            response_text = completion.choices[0].message.content
            
            # Limpiar bloques de razonamiento <think>...</think> de Qwen
            clean_text = clean_thinking_tags(response_text)
            # Limpiar posibles bloques de código markdown de la respuesta
            if clean_text.startswith("```"):
                clean_text = re.sub(r"^```[a-zA-Z]*\n", "", clean_text)
                clean_text = re.sub(r"\n```$", "", clean_text)
                clean_text = clean_text.strip()
                
            data = json.loads(clean_text)
            return data.get("subgroups", [])
        except Exception as e:
            print(f"    [AVISO] Intento {attempt + 1} fallido llamando a Groq (Qwen): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
    return None

def group_news():
    """Ejecuta el proceso completo de agrupación y validación."""
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    news_file = os.path.join(root_dir, 'data', 'news.json')
    
    if not os.path.exists(news_file):
        print(f"Error: No se encontró el archivo de noticias: {news_file}")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news_items = json.load(f)

    # Filtrar resúmenes del día para no procesarlos
    regular_items = [item for item in news_items if not item.get('is_summary')]
    summary_items = [item for item in news_items if item.get('is_summary')]

    if not regular_items:
        print("No hay noticias normales para agrupar.")
        return

    # MIGRACIÓN / RESET DE CACHÉ DE AGRUPACIÓN
    # Si detecta que la versión del algoritmo ha cambiado, resetea la verificación
    # para forzar la re-agrupación de las noticias actuales con las nuevas reglas.
    version_file = os.path.join(root_dir, 'data', '.group_news_version')
    current_version = "2.0"
    force_reset = False
    
    if not os.path.exists(version_file):
        force_reset = True
    else:
        try:
            with open(version_file, 'r', encoding='utf-8') as vf:
                if vf.read().strip() != current_version:
                    force_reset = True
        except:
            force_reset = True

    if force_reset:
        print("    [MIGRACIÓN] Reseteando caché de verificación para aplicar el nuevo algoritmo de agrupación (v2.0)...")
        for item in regular_items:
            item['grouped_verified'] = False
            item['group_id'] = None
        try:
            with open(version_file, 'w', encoding='utf-8') as vf:
                vf.write(current_version)
        except Exception as e:
            print(f"    [AVISO] No se pudo escribir la versión del agrupador: {e}")

    # 1. Agrupar con Jaccard y entidades (mismo algoritmo del frontend)
    tokenized = []
    for item in regular_items:
        title_text = f"{item.get('title', '')} {item.get('original_title', '')}"
        body_text = f"{item.get('body', '')} {item.get('original_body', '')}"
        
        tokenized.append({
            'item': item,
            'title_tokens': tokenize(title_text),
            'body_tokens': tokenize(body_text),
            'title_entities': extract_key_entities(title_text)
        })
        
    n = len(tokenized)
    adj = defaultdict(list)
    for i in range(n):
        for j in range(i + 1, n):
            title_sim = jaccard_similarity(tokenized[i]['title_tokens'], tokenized[j]['title_tokens'])
            body_sim = jaccard_similarity(tokenized[i]['body_tokens'], tokenized[j]['body_tokens'])
            
            ent_i = tokenized[i]['title_entities']
            ent_j = tokenized[j]['title_entities']
            shared_entities = ent_i & ent_j
            
            matched = False
            
            # Regla 1: Similitud Jaccard de título directa (direct matching)
            if title_sim >= 0.20:
                matched = True
            # Regla 2: Similitud Jaccard de body directa
            elif body_sim >= 0.25:
                matched = True
            # Regla 3: Combinación de título + body
            elif title_sim >= 0.05 and body_sim >= 0.11:
                matched = True
            # Regla 4: Entidades clave y overlap
            elif len(shared_entities) >= 2 and body_sim >= 0.08:
                matched = True
            elif ent_i and ent_j and overlap_score(ent_i, ent_j) >= 0.40 and body_sim >= 0.10:
                matched = True
            else:
                # Regla semántica de agresiones (existente, adaptada a la normalización)
                bA = tokenized[i]['body_tokens']
                bB = tokenized[j]['body_tokens']
                shared = bA & bB
                has_weapon = any(w in shared for w in ['blanca', 'cuchilladas', 'navaja', 'cuchillo', 'apunalan', 'acuchillado', 'apunalado'])
                has_back = 'espalda' in shared
                has_young = 'joven' in shared
                
                if has_weapon and has_back and has_young:
                    matched = True
            
            if matched:
                adj[i].append(j)
                adj[j].append(i)
                    
    visited = set()
    candidate_groups = []
    
    for i in range(n):
        if i in visited:
            continue
            
        component = []
        queue = [i]
        visited.add(i)
        
        while queue:
            u = queue.pop(0)
            component.append(u)
            for v in adj[u]:
                if v not in visited:
                    visited.add(v)
                    queue.append(v)
                    
        component.sort()
        candidate_groups.append([tokenized[idx]['item'] for idx in component])

    # 2. Validar candidatos del cluster
    print(f"Total candidatos de Jaccard a validar: {len(candidate_groups)}")
    
    updated_items_map = {item['id']: item for item in regular_items}
    
    for group in candidate_groups:
        if len(group) == 1:
            # Noticia individual
            item = group[0]
            item['group_id'] = None
            item['grouped_verified'] = True
            continue
            
        # Comprobar si todas las noticias en este grupo ya fueron verificadas anteriormente
        all_verified = all(item.get('grouped_verified') == True for item in group)
        
        if all_verified:
            # Mantener sus group_id actuales sin llamar al LLM (ahorrar peticiones de API)
            print(f"    [CACHE] Grupo de {len(group)} elementos ya verificado (IDs: {[x['id'] for x in group]}). Saltando LLM.")
            continue
            
        # Llamar al LLM para resolver o verificar el grupo
        print(f"    [LLM] Validando grupo candidato de {len(group)} noticias con Qwen...")
        subgroups = verify_group_with_llm(group)
        
        if subgroups is None:
            # Fallback en caso de fallo de API
            print("    [FALLBACK] Error al conectar con el LLM. Manteniendo agrupación de Jaccard.")
            fallback_group_id = f"group_{group[0]['id']}"
            for item in group:
                item['group_id'] = fallback_group_id
                # NO se marca como verificado para reintentar en el próximo pipeline run
            continue
            
        # Procesar los subgrupos indicados por la IA
        print(f"    [OK] El LLM dividió el grupo en {len(subgroups)} subgrupos.")
        returned_ids = set()
        
        for sg in subgroups:
            if not sg:
                continue
            returned_ids.update(sg)
            if len(sg) > 1:
                sg_group_id = f"group_{sg[0]}"
                for item_id in sg:
                    if item_id in updated_items_map:
                        updated_items_map[item_id]['group_id'] = sg_group_id
                        updated_items_map[item_id]['grouped_verified'] = True
            else:
                item_id = sg[0]
                if item_id in updated_items_map:
                    updated_items_map[item_id]['group_id'] = None
                    updated_items_map[item_id]['grouped_verified'] = True
                    
        # Robustez: si al LLM se le olvidó algún ID del grupo candidato, tratarlo como individual
        for item in group:
            if item['id'] not in returned_ids:
                print(f"    [WARNING] El LLM omitió la noticia {item['id']}. Marcándola como individual.")
                item['group_id'] = None
                item['grouped_verified'] = True
                
        # Delay de cortesía de medio segundo para mitigar rate limits
        time.sleep(0.5)

    # Reensamblar en el orden original de las noticias
    ordered_ids = [item['id'] for item in regular_items]
    final_regular = [updated_items_map[iid] for iid in ordered_ids]
    
    # Unir con resúmenes del día
    final_news = summary_items + final_regular

    # Guardar en news.json
    with open(news_file, 'w', encoding='utf-8') as f:
        json.dump(final_news, f, indent=2, ensure_ascii=False)
        
    print(f"Proceso finalizado con éxito. news.json guardado.")

if __name__ == "__main__":
    group_news()
