import json
import asyncio
import os
import subprocess
from datetime import datetime, timedelta, timezone
from openai import OpenAI
import edge_tts
from pydub import AudioSegment
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Configuración de OpenRouter
# Usamos el SDK de OpenAI con la URL base de OpenRouter
client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=os.getenv("OPEN_ROUTER"),
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

    # Filtrar noticias de las últimas 24 horas
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

    # Asegurar que tenemos al menos algunas noticias
    if not noticias_hoy:
        print("No hay noticias en las últimas 24h. Usando las últimas 10 del archivo.")
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
    """Genera un guion usando una cascada de modelos gratuitos de OpenRouter."""
    modelos_a_probar = [
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemini-2.0-flash-exp:free",
        "mistralai/mistral-7b-instruct:free",
        "google/gemma-2-9b-it:free"
    ]
    
    prompt = f"""
    Actúa como un guionista de podcasts profesional. Crea un diálogo dinámico e informal entre Alex y María sobre estas noticias de Vitoria. 
    Usa expresiones de España. Devuelve ÚNICAMENTE JSON:
    {{ "dialogo": [ {{ "speaker": "Alex", "text": "..." }}, {{ "speaker": "Maria", "text": "..." }} ] }}
    
    Noticias:
    {texto_origen}
    """
    
    for modelo in modelos_a_probar:
        print(f"--- Intentando generar guion con: {modelo} ---")
        try:
            response = client.chat.completions.create(
                model=modelo,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.8
            )
            return json.loads(response.choices[0].message.content).get("dialogo", [])
        except Exception as e:
            print(f"Fallo con {modelo}: {e}. Probando el siguiente...")
            continue
            
    print("Error: Todos los modelos gratuitos han fallado.")
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
        podcast_final += AudioSegment.from_mp3(archivo)
        podcast_final += AudioSegment.silent(duration=400) 
        os.remove(archivo)
    
    os.rmdir(temp_dir)
    archivo_salida = f"downloads/podcast_local_{datetime.now().strftime('%Y%m%d')}.mp3"
    if not os.path.exists("downloads"): os.makedirs("downloads")
    podcast_final.export(archivo_salida, format="mp3", bitrate="192k")
    print(f"\n¡LISTO! Podcast generado en: {archivo_salida}")

if __name__ == "__main__":
    sincronizar_noticias()
    noticias_texto = convertir_json_a_texto()
    if noticias_texto:
        # 8000 caracteres son suficientes
        guion = generar_guion(noticias_texto[:8000])
        asyncio.run(procesar_podcast(guion))
    else:
        print("Error: No se pudieron obtener noticias.")
