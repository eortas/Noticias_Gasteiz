import os
import json
import time
import subprocess
import re
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

# --- CONFIGURACIÓN ---
REPO_PATH = os.getcwd()
DATA_FILE = os.path.join(REPO_PATH, 'data', 'news.json')
OUTPUT_TXT = os.path.join(REPO_PATH, 'noticias_hoy_notebooklm.txt')
DOWNLOAD_DIR = os.path.join(REPO_PATH, 'downloads')
# Directorio para guardar la sesión de Chrome (Logins de Google y Spotify)
USER_DATA_DIR = os.path.join(REPO_PATH, 'browser_session')

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def update_repo():
    print("--- Paso 0: Sincronizando con GitHub (Opcional) ---")
    try:
        subprocess.run(["git", "pull", "origin", "main"], check=False, capture_output=True)
    except:
        pass

PODCAST_HISTORY = os.path.join(REPO_PATH, 'scraper', 'podcast_history.json')

def prepare_content():
    print("--- Paso 1: Seleccionando noticias NUEVAS para el podcast ---")
    if not os.path.exists(DATA_FILE):
        print(f"Error: No se encuentra {DATA_FILE}")
        return False

    # Cargar noticias actuales
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        noticias = json.load(f)

    # Cargar historial de noticias ya usadas
    historial_ids = []
    if os.path.exists(PODCAST_HISTORY):
        with open(PODCAST_HISTORY, 'r', encoding='utf-8') as f:
            historial_ids = json.load(f)

    noticias_nuevas = []
    for n in noticias:
        n_id = n.get('link')
        if n_id not in historial_ids:
            noticias_nuevas.append(n)

    if not noticias_nuevas:
        print("No hay noticias nuevas desde el último podcast.")
        # Opcional: podrías devolver False aquí si quieres que el script se detenga
        # si no hay nada nuevo. Pero para el ejemplo, devolveremos True si hay al menos una.
        return False

    # Generar el archivo de texto
    count = 0
    with open(OUTPUT_TXT, 'w', encoding='utf-8') as f:
        f.write(f"NOTICIAS NUEVAS DE VITORIA-GASTEIZ - {datetime.now().strftime('%Y-%m-%d')}\n")
        f.write("=" * 60 + "\n\n")
        for n in noticias_nuevas:
            f.write(f"TITULAR: {n.get('title')}\n")
            f.write(f"CONTENIDO: {n.get('body')}\n")
            f.write("-" * 30 + "\n\n")
            historial_ids.append(n.get('link'))
            count += 1
    
    # Guardar el historial actualizado (solo los últimos 500 para no crecer infinito)
    os.makedirs(os.path.dirname(PODCAST_HISTORY), exist_ok=True)
    with open(PODCAST_HISTORY, 'w', encoding='utf-8') as f:
        json.dump(historial_ids[-500:], f, indent=2)

    print(f"Archivo generado con {count} noticias nuevas.")
    return True

def subir_a_spotify(page, audio_path):
    """Lógica para subir el audio a Spotify for Podcasters con manejo de carga lenta."""
    print("--- Paso 5: Spotify for Podcasters ---")
    try:
        # 1. Navegar y esperar carga inicial
        page.goto("https://podcasters.spotify.com/pod/dashboard", wait_until="domcontentloaded")
        
        # --- DETECCIÓN DE LOGIN ---
        if "login" in page.url or page.locator("text=Log in").is_visible():
            print("\n" + "!"*50)
            print("AVISO: NO TIENES SESIÓN INICIADA EN SPOTIFY.")
            print("Por favor, inicia sesión manualmente en la ventana del navegador.")
            print("El script continuará automáticamente cuando llegues al Dashboard.")
            print("!"*50 + "\n")
            page.wait_for_url("**/dashboard**", timeout=0) # Espera infinita al login
        
        print("Esperando a que el dashboard de Spotify cargue...")
        try:
            page.wait_for_selector("text=Nuevo episodio", timeout=45000)
        except:
            print("Carga lenta detectada. Recargando página...")
            page.reload()
            page.wait_for_selector("text=Nuevo episodio", timeout=60000)

        # Intentar pulsar 'Nuevo episodio'
        page.click("text=Nuevo episodio")
        
        print("Preparando la subida del archivo...")
        # Esperar a que aparezca el botón de seleccionar archivo o el área de subida
        try:
            # Buscamos el input de archivos oculto que siempre usa Spotify
            page.wait_for_selector('input[type="file"]', timeout=30000)
            print(f"Subiendo audio: {audio_path}")
            page.set_input_files('input[type="file"]', audio_path)
        except Exception as e:
            print(f"No se detectó el input directo. Intentando vía botón... {e}")
            with page.expect_file_chooser() as fc_info:
                page.click("text=Seleccionar un archivo")
            fc_info.value.set_files(audio_path)
            
        # Rellenar metadatos
        print("Rellenando detalles del episodio...")
        page.wait_for_selector('input[name="title"]', timeout=60000)
        page.fill('input[name="title"]', f"Noticias Vitoria-Gasteiz {datetime.now().strftime('%d/%m/%Y')}")
        
        # Localizar el cuadro de descripción (editor enriquecido)
        print("Escribiendo descripción...")
        desc_box = page.locator('div[role="textbox"], [aria-label*="Descripción"], .ql-editor').first
        desc_box.click()
        desc_box.fill(f"Resumen diario de las noticias más importantes de Vitoria-Gasteiz del día {datetime.now().strftime('%d de %B')}.")
        
        time.sleep(2)
        print("Avanzando al siguiente paso...")
        page.click("button:has-text('Siguiente')")
        
        # Paso de Revisión
        print("Configurando publicación inmediata...")
        page.wait_for_selector("text=Ahora", timeout=30000)
        page.click("text=Ahora")
        
        print("Esperando a que Spotify finalice el procesamiento final...")
        # Esperar a que el botón 'Publicar' esté habilitado y el texto de 'Generando...' desaparezca
        page.wait_for_selector("button:has-text('Publicar'):not([disabled])", timeout=300000)
        
        page.click("button:has-text('Publicar')")
        print("¡PODCAST PUBLICADO EXITOSAMENTE EN SPOTIFY!")
    except Exception as e:
        print(f"Error en el paso de Spotify: {e}")
        page.screenshot(path="downloads/error_spotify.png")
        print("Se ha guardado una captura en downloads/error_spotify.png")

def run_automation():
    audio_path = os.path.join(DOWNLOAD_DIR, f"podcast_{datetime.now().strftime('%Y%m%d')}.wav")
    
    # --- COMPROBACIÓN: SI YA EXISTE EL AUDIO, IR DIRECTO A SPOTIFY ---
    if os.path.exists(audio_path):
        print(f"--- Audio de hoy detectado en: {audio_path} ---")
        print("Saltando generación en NotebookLM y pasando a la subida...")
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=False,
                channel="chrome",
                args=["--disable-blink-features=AutomationControlled"],
                ignore_default_args=["--enable-automation"]
            )
            page = context.pages[0]
            subir_a_spotify(page, audio_path)
            context.close()
        return

    # --- FLUJO NORMAL DE GENERACIÓN ---
    with sync_playwright() as p:
        print("Iniciando navegador Chrome (Modo Stealth)...")
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
            slow_mo=500,
            accept_downloads=True
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

        print("--- Pasos 2-4: NotebookLM (Generación de Audio) ---")
        page.goto("https://notebooklm.google.com/")
        if "accounts.google.com" in page.url:
            print("AVISO: Por favor, inicia sesión en Google.")
            page.wait_for_url("https://notebooklm.google.com/**", timeout=0)

        page.wait_for_load_state("networkidle")
        try:
            nuevo_btn = page.wait_for_selector("text=/Crear cuaderno|Nuevo cuaderno|New notebook/i", timeout=15000)
            nuevo_btn.click()
        except:
            page.click("button:has-text('Crear'), button[aria-label*='notebook'], button[aria-label*='cuaderno']")
        
        print("Subiendo archivo de noticias...")
        time.sleep(2)
        if not page.locator("text=/Crea resúmenes de audio|Añadir fuentes|Subir archivos/i").first.is_visible():
            page.locator("button:has-text('Añadir fuentes'), button:has-text('Add sources'), [aria-label*='fuente']").first.click(force=True)
            time.sleep(2)

        with page.expect_file_chooser(timeout=20000) as fc_info:
            page.locator("button:has-text('Subir archivos'), button:has-text('Upload files')").first.click(force=True)
        fc_info.value.set_files(OUTPUT_TXT)
        
        print("Generando audio (Deep Dive)...")
        page.wait_for_selector("text=/Resumen de audio|Audio Overview/i >> visible=true", timeout=60000)
        page.locator("text=/Resumen de audio|Audio Overview/i").filter(visible=True).first.click(force=True)
        
        print("Configurando duración 'Corto' en NotebookLM...")
        try:
            # 1. Clic en Personalizar (Customize)
            btn_personalizar = page.wait_for_selector("text=/Personalizar|Customize/i", timeout=30000)
            btn_personalizar.click(force=True)
            print("Menú de personalización abierto. Esperando opciones...")
            time.sleep(5) # Más tiempo para que carguen los chips de duración
            
            # 2. Seleccionar 'Corto' (Short)
            print("Seleccionando opción de duración corta...")
            opcion_corto = page.locator("text=/Corto|Short/i").filter(visible=True).first
            opcion_corto.click(timeout=10000)
            time.sleep(2)
            
            # 3. Cerrar menú
            page.keyboard.press("Escape")
            time.sleep(2)
        except Exception as e:
            print(f"Aviso: No se pudo personalizar la duración: {e}")

        # Bucle de generación
        for intento in range(4):
            try:
                print(f"Iniciando generación de audio (Intento {intento+1})...")
                btn_generar = page.locator("text=/Generar|Generate/i").filter(visible=True).first
                btn_generar.click(timeout=10000)
                
                time.sleep(5)
                # Si no sale el mensaje de error de Google, asumimos que ha empezado bien
                if not page.locator("text=/No se ha podido generar/i").filter(visible=True).is_visible():
                    break
                
                print("Google ha rechazado la generación. Limpiando y reintentando...")
                page.locator("text=/Eliminar|Delete/i").filter(visible=True).first.click()
            except Exception as e:
                print(f"Aviso: Intento {intento+1} fallido: {e}")
                time.sleep(5)
        
        print("Esperando descarga (esto tarda varios minutos)...")
        download_btn = page.wait_for_selector('button[aria-label*="Download"], [aria-label*="download"]', timeout=1200000)
        with page.expect_download(timeout=60000) as download_info:
            download_btn.click()
        download_info.value.save_as(audio_path)
        print(f"Audio descargado en: {audio_path}")

        # Pasamos a Spotify
        subir_a_spotify(page, audio_path)
        context.close()

if __name__ == "__main__":
    update_repo()
    if prepare_content():
        run_automation()
    else:
        print("No hay noticias nuevas para procesar.")
