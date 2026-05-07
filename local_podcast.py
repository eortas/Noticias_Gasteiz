import json
import asyncio
import os
import re
from datetime import datetime
from groq import Groq
import edge_tts
from pydub import AudioSegment

# Configuración
# Asegúrate de tener la variable de entorno GROQ_API_KEY configurada
client = Groq() 

# Voces de Microsoft Edge (muy naturales)
VOZ_ALEX = "es-ES-AlvaroNeural"
VOZ_MARIA = "es-ES-ElviraNeural"

def generar_guion(texto_origen):
    """Utiliza Groq para generar un guion dinámico."""
    
    prompt = f"""
    Actúa como un guionista de podcasts profesional. Convierte las noticias de Vitoria-Gasteiz proporcionadas en un diálogo dinámico, 
    informal y muy entretenido entre dos presentadores: Alex (entusiasta y curioso) y María (informada y cercana).
    
    INSTRUCCIONES:
    - Usa expresiones típicas de España y de Vitoria (menciona el clima, el Alavés, o frases como '¡qué pasa, Gasteiz!').
    - El diálogo debe ser fluido, con Alex haciendo preguntas y María dando los detalles.
    - No leas las noticias tal cual; resúmelas como si se las contaras a un amigo tomando un café en la Plaza de la Virgen Blanca.
    - La duración total debe ser de unos 3-5 minutos de lectura.
    
    Devuelve ÚNICAMENTE un objeto JSON válido con esta estructura:
    {{
      "dialogo": [
        {{"speaker": "Alex", "text": "..."}},
        {{"speaker": "Maria", "text": "..."}}
      ]
    }}
    
    Noticias de hoy:
    {texto_origen}
    """
    
    print("--- Paso 1: Generando guion con Groq (Llama 3) ---")
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-70b-8192",
            response_format={"type": "json_object"},
            temperature=0.8
        )
        
        contenido = json.loads(chat_completion.choices[0].message.content)
        return contenido.get("dialogo", [])
    except Exception as e:
        print(f"Error al generar guion: {e}")
        return []

async def generar_audio_fragmento(texto, voz, archivo_salida):
    """Genera un archivo MP3 para un fragmento usando edge-tts."""
    communicate = edge_tts.Communicate(texto, voz)
    await communicate.save(archivo_salida)

async def procesar_podcast(guion):
    """Genera voces y une el audio final."""
    if not guion:
        print("No hay guion para procesar.")
        return

    temp_dir = "temp_audio"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    archivos_temporales = []
    
    print("--- Paso 2: Generando voces con Edge-TTS ---")
    for i, linea in enumerate(guion):
        speaker = linea['speaker']
        text = linea['text']
        
        voz = VOZ_ALEX if speaker.lower() == "alex" else VOZ_MARIA
        archivo_temp = os.path.join(temp_dir, f"temp_{i:03d}.mp3")
        archivos_temporales.append(archivo_temp)
        
        await generar_audio_fragmento(text, voz, archivo_temp)
        if i % 5 == 0:
            print(f"  Procesando fragmento {i+1}/{len(guion)}...")

    print("--- Paso 3: Mezclando y uniendo audio final ---")
    podcast_final = AudioSegment.empty()
    
    for archivo in archivos_temporales:
        try:
            fragmento = AudioSegment.from_mp3(archivo)
            podcast_final += fragmento
            # Pausa natural de 400ms entre intervenciones
            podcast_final += AudioSegment.silent(duration=400) 
        except Exception as e:
            print(f"Error al procesar {archivo}: {e}")

    # Exportar resultado
    fecha_hoy = datetime.now().strftime("%Y%m%d")
    archivo_salida = f"downloads/podcast_local_{fecha_hoy}.mp3"
    
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
        
    podcast_final.export(archivo_salida, format="mp3", bitrate="192k")
    print(f"\n¡ÉXITO! Podcast generado: {archivo_salida}")

    # Limpieza
    for archivo in archivos_temporales:
        os.remove(archivo)
    os.rmdir(temp_dir)

if __name__ == "__main__":
    INPUT_FILE = "noticias_hoy_notebooklm.txt"
    
    if not os.path.exists(INPUT_FILE):
        print(f"Error: No se encuentra {INPUT_FILE}. Ejecuta primero el pipeline.")
    else:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            contenido_noticias = f.read()
        
        # Limitar texto si es demasiado largo para el contexto de Groq (aunque Llama3 tiene mucho margen)
        guion = generar_guion(contenido_noticias[:15000]) 
        asyncio.run(procesar_podcast(guion))
