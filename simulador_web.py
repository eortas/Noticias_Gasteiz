import time
import random
import subprocess
import os
from datetime import datetime

# URL de la web a abrir
URL = "https://gasteizlive.pages.dev/"

# Navegador a usar (chrome.exe, msedge.exe, etc.)
# Nota: En Windows, 'start chrome' forzará la apertura en Chrome.
BROWSER_EXE = "chrome.exe" 

def open_browser():
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] Abriendo web: {URL}")
    # Forzamos la apertura en Chrome
    subprocess.Popen(f"start chrome {URL}", shell=True)

def close_browser():
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] Cerrando navegador...")
    # taskkill cierra el proceso. /F fuerza el cierre, /T cierra procesos hijos
    try:
        subprocess.run(["taskkill", "/F", "/IM", BROWSER_EXE, "/T"], capture_output=True)
    except Exception as e:
        print(f"Error al cerrar: {e}")

def main():
    print("=== Simulador de Sesiones de Navegación ===")
    print(f"URL: {URL}")
    print(f"Ciclo: Cada 5 minutos")
    print(f"Tiempo abierto: Aleatorio entre 2:00 y 4:40")
    print("Presiona Ctrl+C para detener el script.\n")
    
    while True:
        cycle_start = time.time()
        
        # 1. Abrir la web
        open_browser()
        
        # 2. Calcular tiempo aleatorio de sesión (120 a 280 segundos)
        session_seconds = random.randint(120, 280)
        mins = session_seconds // 60
        secs = session_seconds % 60
        print(f"-> Sesión activa por {mins}m {secs}s")
        
        # 3. Esperar el tiempo de la sesión
        time.sleep(session_seconds)
        
        # 4. Cerrar el navegador
        close_browser()
        
        # 5. Calcular cuánto tiempo queda para llegar a los 5 minutos (300 segundos)
        total_cycle = 300
        elapsed = time.time() - cycle_start
        wait_until_next = max(1, total_cycle - elapsed)
        
        print(f"-> Esperando {int(wait_until_next)}s hasta el próximo ciclo de 5 min...\n")
        time.sleep(wait_until_next)

if __name__ == "__main__":
    main()
