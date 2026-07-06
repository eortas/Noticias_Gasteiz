import subprocess
import sys
import os
import json

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

def check_and_fix_images():
    """Check if any news are missing images and fix them if needed."""
    news_file = "data/news.json"
    if not os.path.exists(news_file):
        return True  # No news file yet, nothing to fix
    
    with open(news_file, 'r', encoding='utf-8') as f:
        news = json.load(f)
    
    missing = [n for n in news if not n.get('image') or n.get('image') == '']
    print(f"\n>>> Verificando imágenes faltantes...")
    print(f"    Noticias sin imagen: {len(missing)}")
    
    if missing:
        print(f"    Ejecutando fix_missing_images_ddg.py...")
        return run_script("scraper/fix_missing_images_ddg.py")
    else:
        print(f"    [OK] Todas las noticias tienen imagen.")
        return True

if __name__ == "__main__":
    # Aseguramos que estamos en el directorio raíz
    root_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root_dir)

    scripts = [
        "scraper/multi_scraper.py",
        "scraper/filter_sponsored.py",
        "scraper/parallel_rewrite.py",
        "scraper/group_news.py",
        "scraper/update_mood.py",
        "scraper/generate_summary.py",
        "scraper/update_podcast.py",
        "scraper/enviar_telegram.py"
    ]
    
    for script in scripts:
        if not run_script(script):
            print("\n[ERROR] El proceso se detuvo por un error.")
            sys.exit(1)
    
    # Check and fix missing images as a safety net
    if not check_and_fix_images():
        print("\n[WARN] No se pudieron reparar todas las imágenes, pero se continúa con el proceso.")
    
    print("\n*** Actualización completa finalizada con éxito. ***")