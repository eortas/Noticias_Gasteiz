import json
import asyncio
import os
import subprocess
from datetime import datetime, timedelta, timezone
from groq import Groq
import edge_tts
from pydub import AudioSegment

# Configuración
client = Groq() 
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
            # Intentar parsear fecha ISO
            fecha_n = datetime.fromisoformat(n['date'].replace('Z', '+00:00'))
            if fecha_n >= hace_24h:
                noticias_hoy.append(n)
        except:
            continue

    if not noticias_hoy:
        print("No hay noticias en las últimas 24h. Usando las últimas 10 disponibles.")
        noticias_hoy = news[:10]

    texto_final = f"NOTICIAS DE VITORIA-GASTEIZ - {datetime.now().strftime('%Y-%m-%d')}\n"
    texto_final += "="*60 + "\n\n"

    for i, n in enumerate(noticias_hoy):
        texto_final += f"TITULAR: {n['title']}\n"
        # Si tiene body/resumen lo incluimos (asumiendo que el JSON lo tiene o lo simulamos)
        cuerpo = n.get('body', 'Sin descripción adicional.')
        texto_final += f"CONTENIDO: {cuerpo}\n"
        texto_final += "-"*30 + "\n\n"
    
    return texto_final

def generar_guion(texto_origen):
    """Utiliza Groq para generar un guion dinámico."""
    prompt = f"""
    Actúa como un guionista de podcasts profesional. Convierte las noticias de Vitoria-Gasteiz proporcionadas en un diálogo dinámico, 
    informal y muy entretenido entre dos presentadores: Alex (entusiasta) y María (cercana).
    
    - Usa expresiones de España y Vitoria.
    - Diálogo fluido y natural.
    - No leas las noticias; cuéntalas.
    
    Devuelve ÚNICAMENTE un objeto JSON:
    {{ "dialogo": [ {{ "speaker": "Alex", "text": "..." }}, {{ "speaker": "Maria", "text": "..." }} ] }}
    
    Noticias:
    {texto_origen}
    """
    
    print("--- Paso 2: Generando guion con Groq (Llama 3) ---")
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-70b-8192",
            response_format={"type": "json_object"},
            temperature=0.8
        )
        return json.loads(chat_completion.choices[0].message.content).get("dialogo", [])
    except Exception as e:
        print(f"Error en Groq: {e}")
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
        guion = generar_guion(noticias_texto[:15000])
        asyncio.run(procesar_podcast(guion))
    else:
        print("Error: No se pudieron obtener noticias.")
