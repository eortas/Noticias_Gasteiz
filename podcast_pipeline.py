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
        # Intentamos un pull simple. Si falla por cambios locales, no pasa nada,
        # seguiremos con lo que tenemos en local.
        subprocess.run(["git", "pull", "origin", "main"], check=False, capture_output=True)
    except:
        pass

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

        # Esperar a que la página cargue y buscar el botón de nuevo cuaderno
        print("Esperando a que NotebookLM cargue por completo...")
        page.wait_for_load_state("networkidle")
        
        # Intentar clicar en 'Crear cuaderno' o 'New notebook' usando Regex
        try:
            nuevo_btn = page.wait_for_selector("text=/Crear cuaderno|Nuevo cuaderno|New notebook/i", timeout=15000)
            nuevo_btn.click()
        except:
            print("No se encontró el botón con texto. Intentando por selector de icono...")
            # Fallback: El botón de arriba a la derecha
            page.click("button:has-text('Crear'), button[aria-label*='notebook'], button[aria-label*='cuaderno']")
        
        # Subir archivo
        print("Subiendo archivo de noticias...")
        time.sleep(2) # Esperar a que el posible diálogo automático aparezca
        
        # 1. Comprobar si el diálogo de fuentes ya está abierto (como se ve en tu captura)
        if not page.locator("text=/Crea resúmenes de audio|Añadir fuentes|Subir archivos/i").first.is_visible():
            print("Abriendo menú de fuentes manualmente...")
            page.locator("button:has-text('Añadir fuentes'), button:has-text('Add sources'), [aria-label*='fuente']").first.click(force=True)
            time.sleep(2)

        # 2. Clic en el botón específico 'Subir archivos' que vemos en la imagen
        print("Seleccionando 'Subir archivos' del panel central...")
        try:
            with page.expect_file_chooser(timeout=20000) as fc_info:
                # El botón exacto que sale en tu captura
                page.locator("button:has-text('Subir archivos'), button:has-text('Upload files')").first.click(force=True)
            
            file_chooser = fc_info.value
            file_chooser.set_files(OUTPUT_TXT)
            print("Archivo seleccionado con éxito.")
        except Exception as e:
            print(f"No se detectó el botón principal. Probando alternativas...")
            # Fallback por si el botón tiene otro nombre o es una tarjeta
            with page.expect_file_chooser(timeout=15000) as fc_info:
                page.locator("text=/Subir|Upload|Ordenador|Computer|Archivo|File/i").first.click(force=True)
            print("Archivo seleccionado con éxito. Esperando 20s a que NotebookLM procese la fuente...")
            time.sleep(20)
        except Exception as e:
            print(f"Error crítico en la subida: {e}")
            page.screenshot(path=os.path.join(DOWNLOAD_DIR, "error_notebooklm.png"))
            print(f"Se ha guardado una captura del error en: {DOWNLOAD_DIR}/error_notebooklm.png")
            raise e
        
        print("Fuente procesada. Iniciando generación de audio en el panel Studio...")
        # Usamos .filter(visible=True) para evitar elementos ocultos de accesibilidad
        try:
            # Esperamos a que el panel Studio sea visible
            page.wait_for_selector("text=/Resumen de audio|Audio Overview/i >> visible=true", timeout=60000)
            time.sleep(2)
            
            # Clic en el botón visible
            audio_btn = page.locator("text=/Resumen de audio|Audio Overview/i").filter(visible=True).first
            audio_btn.click(force=True)
            print("Panel de audio abierto.")
        except Exception as e:
            print(f"No se pudo clicar directamente: {e}. Probando vía Guía...")
            try:
                page.locator("text=/Guía del cuaderno|Notebook Guide/i").filter(visible=True).first.click(timeout=10000)
                time.sleep(2)
                page.locator("text=/Resumen de audio|Audio Overview/i").filter(visible=True).first.click(force=True)
            except:
                print("Fallo total al encontrar el botón de audio. Guardando captura...")
                page.screenshot(path=os.path.join(DOWNLOAD_DIR, "error_studio.png"))
                raise e
        
        # Click en Generar Audio (Deep Dive) con reintentos para fallos de Google
        print("Iniciando fase de generación...")
        for intento in range(3):
            try:
                # Comprobar si sale el error de Google "No se ha podido generar"
                error_msg = page.locator("text=/No se ha podido generar|Could not generate/i").filter(visible=True)
                if error_msg.is_visible():
                    print(f"Detectado error de Google (intento {intento+1}). Reintentando...")
                    page.locator("text=/Eliminar|Delete|Remove/i").filter(visible=True).first.click()
                    time.sleep(2)
                    page.locator("text=/Resumen de audio|Audio Overview/i").filter(visible=True).first.click(force=True)
                    time.sleep(3)

                print("Buscando botón 'Generar'...")
                btn_generar = page.locator("text=/Generar|Generate/i").filter(visible=True).first
                btn_generar.wait_for(timeout=30000)
                btn_generar.click()
                break # Éxito
            except Exception as e:
                if intento == 2: raise e
                print(f"Fallo al iniciar generación. Reintentando clic en Resumen de audio... ({intento + 1}/3)")
                page.locator("text=/Resumen de audio|Audio Overview/i").filter(visible=True).first.click(force=True)
                time.sleep(5)
        
        print("Generando audio... esto puede tardar varios minutos (normalmente 2-5 min).")
        # Esperar a que el botón de descarga esté disponible (timeout de 10 min)
        # El selector del botón de descarga suele ser un icono de descarga (download)
        download_btn = page.wait_for_selector('button[aria-label*="Download"], button[aria-label*="descargar"]', timeout=600000)
        
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
