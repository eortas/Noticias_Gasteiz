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

def tokenize(text):
    """Tokeniza un texto eliminando palabras vacías y caracteres especiales (igual que en app.js)."""
    if not text:
        return set()
    stopwords = {
        'de', 'la', 'el', 'en', 'y', 'a', 'los', 'un', 'una', 'con', 'para', 'este', 'esta', 'por', 'del', 
        'al', 'se', 'las', 'su', 'sus', 'o', 'u', 'como', 'que', 'lo', 'uno', 'unas', 'unos',
        'correo', 'gasteiz', 'hoy', 'noticias', 'alava', 'vitoria', 'diario', 'araba', 'html', 'htm'
    }
    text = text.lower()
    text = re.sub(r'[.,\/#!$%\^&\*;:{}=\-_`~()?"\'\n\r0-9]', ' ', text)
    words = text.split()
    return {w for w in words if len(w) > 2 and w not in stopwords}

def jaccard_similarity(set_a, set_b):
    """Calcula el índice de similitud de Jaccard entre dos conjuntos."""
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)

def extract_key_entities(text):
    """Extrae entidades clave (nombres propios, siglas) del texto original (antes de lowercase)."""
    if not text:
        return set()
    # Stopwords ampliadas: palabras comunes que aparecen capitalizadas por estar al inicio de frase
    entity_stopwords = {
        'el', 'la', 'los', 'las', 'un', 'una', 'de', 'del', 'en', 'con', 'por', 'para',
        'que', 'se', 'al', 'su', 'sus', 'es', 'son', 'ha', 'han', 'ser', 'fue', 'como',
        'este', 'esta', 'estos', 'estas', 'ese', 'esa', 'esos', 'esas', 'hay', 'más',
        'no', 'si', 'ya', 'pero', 'sin', 'sobre', 'entre', 'tras', 'ante', 'bajo',
        'también', 'según', 'además', 'nuevo', 'nueva', 'nuevos', 'nuevas',
        'gran', 'todo', 'toda', 'todos', 'todas', 'otro', 'otra', 'otros', 'otras',
        'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve', 'diez',
        'vitoria', 'gasteiz', 'álava', 'araba', 'alava', 'euskadi',
        'correo', 'diario', 'noticias', 'hoy',
    }
    # Limpiar caracteres especiales pero mantener mayúsculas
    clean = re.sub(r'[.,\/#!$%\^&\*;:{}=\-_`~()?"\'\n\r0-9]', ' ', text)
    words = clean.split()
    entities = set()
    for w in words:
        # Capturar palabras que empiezan en mayúscula (nombres propios)
        # o son siglas (todo mayúsculas, al menos 2 letras)
        if len(w) < 2:
            continue
        if w.lower() in entity_stopwords:
            continue
        if w[0].isupper() or w.isupper():
            entities.add(w.lower())
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

    # 1. Agrupar con Jaccard (mismo algoritmo del frontend)
    tokenized = []
    for item in regular_items:
        url_words = ""
        if item.get('url'):
            try:
                parsed_url = urllib.parse.urlparse(item['url'])
                url_words = parsed_url.path
            except Exception:
                url_words = item['url']
            url_words = re.sub(r'[\/\-_.]', ' ', url_words)
            url_words = re.sub(r'\d+', '', url_words)
            
        title_text = f"{item.get('title', '')} {item.get('original_title', '')} {url_words}"
        body_text = f"{item.get('body', '')} {item.get('original_body', '')}"
        
        # Texto original sin lowercase para extraer entidades (nombres propios)
        title_raw = f"{item.get('title', '')} {item.get('original_title', '')}"
        
        tokenized.append({
            'item': item,
            'title_tokens': tokenize(title_text),
            'body_tokens': tokenize(body_text),
            'title_entities': extract_key_entities(title_raw)
        })
        
    n = len(tokenized)
    adj = defaultdict(list)
    for i in range(n):
        for j in range(i + 1, n):
            title_sim = jaccard_similarity(tokenized[i]['title_tokens'], tokenized[j]['title_tokens'])
            body_sim = jaccard_similarity(tokenized[i]['body_tokens'], tokenized[j]['body_tokens'])
            
            # Regla 1-3: Similitud Jaccard (umbrales ligeramente relajados para generar más candidatos que el LLM verificará)
            if title_sim >= 0.22 or body_sim >= 0.28 or (title_sim >= 0.06 and body_sim >= 0.13):
                adj[i].append(j)
                adj[j].append(i)
            else:
                # Regla 4: Entidades clave compartidas + overlap del body
                # Captura noticias con nombres propios comunes aunque usen vocabulario distinto
                ent_i = tokenized[i]['title_entities']
                ent_j = tokenized[j]['title_entities']
                shared_entities = ent_i & ent_j
                body_overlap = overlap_score(tokenized[i]['body_tokens'], tokenized[j]['body_tokens'])
                
                # Si comparten al menos 2 entidades clave en el título y algo de overlap en body
                if len(shared_entities) >= 2 and body_overlap >= 0.12:
                    adj[i].append(j)
                    adj[j].append(i)
                # Si hay alta similitud de entidades (proporción) con algo de overlap en body
                elif ent_i and ent_j and overlap_score(ent_i, ent_j) >= 0.35 and body_overlap >= 0.18:
                    adj[i].append(j)
                    adj[j].append(i)
                # Regla 5: Body overlap muy alto indica mismo tema aunque títulos difieran
                # (el LLM validará después para evitar falsos positivos)
                elif body_overlap >= 0.25 and title_sim >= 0.03:
                    adj[i].append(j)
                    adj[j].append(i)
                else:
                    # Regla semántica de agresiones (existente)
                    bA = tokenized[i]['body_tokens']
                    bB = tokenized[j]['body_tokens']
                    shared = bA & bB
                    has_weapon = any(w in shared for w in ['blanca', 'cuchilladas', 'navaja', 'cuchillo', 'apuñalan', 'acuchillado', 'apuñalado'])
                    has_back = 'espalda' in shared
                    has_young = 'joven' in shared
                    
                    if has_weapon and has_back and has_young:
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
