import time
import random
import subprocess
import os
from datetime import datetime

# URL de la web a abrir
URL = "https://gasteizlive.vercel.app/"

# Navegador a usar (chrome.exe, msedge.exe, etc.)
# Nota: En Windows, 'start chrome' forzará la apertura en Chrome.
BROWSER_EXE = "chrome.exe" 

def open_browser():
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] Abriendo web (minimizado): {URL}")
    # Intentamos abrir minimizado y en una ventana nueva para mayor efectividad
    subprocess.Popen(f"start /min chrome --new-window {URL}", shell=True)

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
    print(f"Pausa entre sesiones: 5-10 segundos")
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
        
        # 5. Esperar un tiempo corto antes del siguiente ciclo (entre 5 y 10 segundos)
        wait_until_next = random.randint(5, 10)
        
        print(f"-> Esperando {int(wait_until_next)}s hasta el próximo ciclo...\n")
        time.sleep(wait_until_next)

if __name__ == "__main__":
    main()
