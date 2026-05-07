import json
import asyncio
import os
import subprocess
import shutil
from datetime import datetime, timedelta, timezone
from openai import OpenAI
import edge_tts
from pydub import AudioSegment
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Configuración de Clientes (NVIDIA como primario, OpenRouter como backup)
def get_ai_client(provider="nvidia"):
    if provider == "nvidia":
        return OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.getenv("NVIDIA_API")
        )
    else:
        return OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPEN_ROUTER")
        )

VOZ_ALEX = "es-ES-AlvaroNeural"
VOZ_MARIA = "es-ES-ElviraNeural"

def sincronizar_noticias():
    """Baja las últimas noticias de GitHub."""
    print("--- Paso 0: Sincronizando con GitHub ---")
    try:
        subprocess.run(["git", "pull", "origin", "main"], check=True)
        print("Sincronización completada.")
    except Exception as e:
        print(f"Aviso: No se pudo sincronizar (usando datos locales): {e}")

def convertir_json_a_texto(json_file="data/news.json"):
    """Convierte el JSON de noticias a texto plano para la IA."""
    print("--- Paso 1: Procesando noticias recientes ---")
    if not os.path.exists(json_file):
        return None

    with open(json_file, 'r', encoding='utf-8') as f:
        news = json.load(f)

    ahora = datetime.now(timezone.utc)
    hace_24h = ahora - timedelta(hours=24)
    
    noticias_hoy = []
    for n in news:
        try:
            fecha_n = datetime.fromisoformat(n['date'].replace('Z', '+00:00'))
            if fecha_n >= hace_24h:
                noticias_hoy.append(n)
        except:
            continue

    if not noticias_hoy:
        noticias_hoy = news[:10]
    else:
        noticias_hoy = noticias_hoy[:10]

    noticias_chunks = []
    for i, n in enumerate(noticias_hoy):
        chunk = f"[NOTICIA {i+1}]\nTITULAR: {n['title']}\n"
        cuerpo = n.get('body', 'Sin descripción.')
        chunk += f"RESUMEN: {cuerpo[:600]}...\n"
        noticias_chunks.append(chunk)
    
    return "\n\n".join(noticias_chunks)

def generar_guion(texto_origen):
    """Genera un guion usando NVIDIA como fuente principal."""
    modelos_nvidia = [
        "meta/llama-3.1-70b-instruct",
        "meta/llama-3.3-70b-instruct",
        "nvidia/llama-3.1-nemotron-70b-instruct"
    ]
    
    prompt = f"""
    Actúa como un guionista de podcasts profesional. Crea un diálogo dinámico e informal entre Alex y María sobre estas noticias de Vitoria. 
    Usa expresiones de España. Devuelve ÚNICAMENTE JSON con la estructura:
    {{ "dialogo": [ {{ "speaker": "Alex", "text": "..." }}, {{ "speaker": "Maria", "text": "..." }} ] }}
    
    Noticias:
    {texto_origen}
    """
    
    client_nv = get_ai_client("nvidia")
    for modelo in modelos_nvidia:
        print(f"--- Intentando con NVIDIA: {modelo} ---")
        try:
            response = client_nv.chat.completions.create(
                model=modelo,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.8
            )
            return json.loads(response.choices[0].message.content).get("dialogo", [])
        except Exception as e:
            print(f"Fallo NVIDIA {modelo}: {e}")
            continue

    print("NVIDIA ha fallado. Usando OpenRouter como respaldo...")
    client_or = get_ai_client("openrouter")
    modelos_or = ["deepseek/deepseek-r1:free", "meta-llama/llama-3.1-8b-instruct:free"]
    for modelo in modelos_or:
        try:
            response = client_or.chat.completions.create(
                model=modelo,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.8
            )
            return json.loads(response.choices[0].message.content).get("dialogo", [])
        except:
            continue
            
    print("Error: Todos los proveedores han fallado.")
    return []

async def generar_audio_fragmento(texto, voz, archivo_salida):
    communicate = edge_tts.Communicate(texto, voz)
    await communicate.save(archivo_salida)

async def procesar_podcast(guion):
    if not guion: return
    temp_dir = "temp_audio"
    if not os.path.exists(temp_dir): os.makedirs(temp_dir)
    
    archivos_temporales = []
    print("--- Paso 3: Generando voces con Edge-TTS ---")
    for i, linea in enumerate(guion):
        voz = VOZ_ALEX if linea['speaker'].lower() == "alex" else VOZ_MARIA
        archivo_temp = os.path.join(temp_dir, f"temp_{i:03d}.mp3")
        archivos_temporales.append(archivo_temp)
        await generar_audio_fragmento(linea['text'], voz, archivo_temp)
    
    print("--- Paso 4: Uniendo audio final ---")
    podcast_final = AudioSegment.empty()
    for archivo in archivos_temporales:
        try:
            podcast_final += AudioSegment.from_mp3(archivo)
            podcast_final += AudioSegment.silent(duration=400) 
        except:
            continue
    
    archivo_salida = os.path.abspath(f"downloads/podcast_local_{datetime.now().strftime('%Y%m%d')}.mp3")
    if not os.path.exists("downloads"): os.makedirs("downloads")
    
    if len(podcast_final) > 0:
        podcast_final.export(archivo_salida, format="mp3", bitrate="192k")
        print(f"\n¡ÉXITO! Podcast generado en: {archivo_salida}")
    else:
        print("\nERROR: El audio final está vacío. Revisa las voces de Edge-TTS.")

    # Limpieza robusta en Windows
    try:
        shutil.rmtree(temp_dir)
    except:
        pass

if __name__ == "__main__":
    sincronizar_noticias()
    noticias_texto = convertir_json_a_texto()
    if noticias_texto:
        guion = generar_guion(noticias_texto[:8000])
        if guion:
            # Guardar el guion para que el usuario pueda verlo
            fecha_str = datetime.now().strftime('%Y%m%d')
            archivo_guion = os.path.abspath(f"downloads/guion_{fecha_str}.json")
            if not os.path.exists("downloads"): os.makedirs("downloads")
            with open(archivo_guion, 'w', encoding='utf-8') as f:
                json.dump(guion, f, indent=2, ensure_ascii=False)
            print(f"Guion guardado en: {archivo_guion}")
            
            asyncio.run(procesar_podcast(guion))
    else:
        print("Error: No se pudieron obtener noticias.")
