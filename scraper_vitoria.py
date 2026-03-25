import sys
import os

# Aseguramos que el script pueda encontrar el módulo scraper si se ejecuta desde la raíz
sys.path.append(os.path.join(os.path.dirname(__file__), 'scraper'))

from scraper.multi_scraper import MultiScraper

def main():
    print("=== Vitoria Chronicle Multi-Source Scraper ===")
    print("Iniciando recolección de noticias desde El Correo, DNA y Gasteiz Hoy...\n")
    
    scraper = MultiScraper()
    scraper.run()
    
    print("\n=== Proceso Finalizado ===")
    print(f"Los datos se han guardado en: {scraper.data_output}")
    print("Puedes ver los resultados ejecutando 'npm run dev' y visitando el portal.")

if __name__ == "__main__":
    main()
