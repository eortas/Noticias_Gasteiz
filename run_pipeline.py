import subprocess
import sys
import os

def run_script(script_path):
    print(f"\n>>> Ejecutando {script_path}...")
    try:
        # Usamos sys.executable para asegurar que usamos el mismo python que este script
        subprocess.run([sys.executable, script_path], check=True)
        print(f"[OK] {script_path} completado con éxito.")
    except subprocess.CalledProcessError as e:
        print(f"X Error al ejecutar {script_path}: {e}")
        return False
    except FileNotFoundError:
        print(f"X Error: No se encontró el archivo {script_path}")
        return False
    return True

if __name__ == "__main__":
    # Aseguramos que estamos en el directorio raíz
    root_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root_dir)

    scripts = [
        "scraper/multi_scraper.py",
        "scraper/parallel_rewrite.py",
        "scraper/update_mood.py",
        "scraper/update_podcast.py",
        "scraper/enviar_telegram.py"
    ]
    
    for script in scripts:
        if not run_script(script):
            print("\n[ERROR] El proceso se detuvo por un error.")
            sys.exit(1)
    
    print("\n*** Actualización completa finalizada con éxito. ***")
