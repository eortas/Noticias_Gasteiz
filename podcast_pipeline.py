import os
import json
import time
import subprocess
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
    print("--- Paso 0: Descargando últimas noticias de GitHub ---")
    try:
        # Hacemos stash por si hay cambios locales (como el JSON de noticias)
        subprocess.run(["git", "stash"], check=False)
        subprocess.run(["git", "pull", "origin", "main", "--rebase"], check=True)
        subprocess.run(["git", "stash", "pop"], check=False)
    except Exception as e:
        print(f"Aviso: No se pudo sincronizar con GitHub (pero el script continuará): {e}")

def prepare_content():
    print("--- Paso 1: Convirtiendo JSON a Texto para NotebookLM ---")
    if not os.path.exists(DATA_FILE):
        print(f"Error: No se encuentra {DATA_FILE}")
        return False

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        noticias = json.load(f)

    # Filtrar noticias de las últimas 24 horas para el podcast
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    # También incluimos ayer por si el podcast se graba temprano
    fecha_ayer = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    count = 0
    with open(OUTPUT_TXT, 'w', encoding='utf-8') as f:
        f.write(f"NOTICIAS DE VITORIA-GASTEIZ - {fecha_hoy}\n")
        f.write("=" * 60 + "\n\n")
        for n in noticias:
            f_noticia = n.get('date', '')[:10]
            if f_noticia in [fecha_hoy, fecha_ayer]:
                f.write(f"TITULAR: {n.get('title')}\n")
                f.write(f"CONTENIDO: {n.get('body')}\n")
                f.write("-" * 30 + "\n\n")
                count += 1
    
    print(f"Archivo generado con {count} noticias.")
    return count > 0

def run_automation():
    with sync_playwright() as p:
        # Usamos launch_persistent_context para no tener que loguearnos cada vez
        # La primera vez que lo corras, verás el navegador. Loguéate y cierra.
        print("Iniciando navegador Chrome (Modo Stealth)...")
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            channel="chrome", # Usar el Chrome del sistema
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
            slow_mo=500,
            accept_downloads=True
        )
        page = context.new_page()
        
        # Inyectar script para ocultar automatización (Stealth Nativo)
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        # --- NOTEBOOK LM ---
        print("--- Pasos 2-4: NotebookLM (Generación de Audio) ---")
        page.goto("https://notebooklm.google.com/")
        
        # Comprobar si estamos logueados
        if "accounts.google.com" in page.url:
            print("AVISO: Por favor, inicia sesión en Google en la ventana del navegador.")
            page.wait_for_url("https://notebooklm.google.com/**", timeout=0)

        # Crear nuevo cuaderno
        page.click("text=Nuevo cuaderno")
        
        # Subir archivo
        # Esperamos al input de archivos
        with page.expect_file_chooser() as fc_info:
            page.click("text=Cargar") # O el botón de upload
        file_chooser = fc_info.value
        file_chooser.set_files(OUTPUT_TXT)
        
        print("Archivo subido. Generando Audio Overview...")
        # Los selectores de NotebookLM pueden variar, estos son aproximados
        # Debes verificar los IDs reales en tu cuenta
        page.wait_for_selector("text=Notebook Guide", timeout=60000)
        page.click("text=Notebook Guide")
        
        # Click en Generar Audio (Deep Dive)
        page.click("text=Generate")
        
        print("Generando audio... esto puede tardar varios minutos.")
        # Esperar a que el botón de descarga esté disponible (timeout de 10 min)
        download_btn = page.wait_for_selector('button[aria-label*="Download"]', timeout=600000)
        
        with page.expect_download() as download_info:
            download_btn.click()
        
        download = download_info.value
        audio_path = os.path.join(DOWNLOAD_DIR, f"podcast_{datetime.now().strftime('%Y%m%d')}.wav")
        download.save_as(audio_path)
        print(f"Audio descargado en: {audio_path}")

        # --- SPOTIFY ---
        print("--- Paso 5: Spotify for Podcasters ---")
        page.goto("https://podcasters.spotify.com/pod/dashboard")
        
        if "login" in page.url:
            print("AVISO: Por favor, inicia sesión en Spotify en la ventana del navegador.")
            page.wait_for_url("**/dashboard**", timeout=0)

        page.click("text=Nuevo episodio")
        page.click("text=Subida rápida") # O similar
        
        # Subir el audio
        page.set_input_files('input[type="file"]', audio_path)
        
        # Rellenar metadatos
        page.fill('input[name="title"]', f"Noticias Vitoria-Gasteiz {datetime.now().strftime('%d/%m/%Y')}")
        page.fill('textarea[name="description"]', f"Resumen diario de las noticias más importantes de Vitoria-Gasteiz del día {datetime.now().strftime('%d de %B')}.")
        
        print("Esperando a que Spotify procese el audio...")
        page.wait_for_selector("text=Procesamiento completado", timeout=300000)
        
        page.click("text=Publicar ahora")
        print("¡PODCAST PUBLICADO EN SPOTIFY!")

        context.close()

if __name__ == "__main__":
    update_repo()
    if prepare_content():
        run_automation()
    else:
        print("No hay noticias nuevas para procesar.")
