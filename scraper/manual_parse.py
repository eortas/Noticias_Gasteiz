import cloudscraper
from bs4 import BeautifulSoup
import sys

def parse_manual_link(url):
    print(f"\n--- Intentando extraer: {url} ---")
    
    # Configuramos el scraper igual que en el multi_scraper
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    
    # Cabeceras que a veces ayudan a ver más contenido (simulando Googlebot o referer)
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
        'Referer': 'https://www.google.com/'
    }

    try:
        response = scraper.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Error: No se pudo acceder a la página (Código: {response.status_code})")
            return

        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. Extraer Título
        title = ""
        title_tag = soup.find('h1')
        if title_tag:
            title = title_tag.get_text().strip()
        else:
            title = soup.title.string if soup.title else "Sin título"

        # 2. Extraer Cuerpo (técnica El Correo)
        body_parts = []
        
        # Intentamos buscar en el contenedor principal de la noticia
        content = soup.find('div', class_='v-p-b') or \
                  soup.find('div', class_='entry-content') or \
                  soup.find('article') or \
                  soup.find('div', class_='voc-story')
        
        if content:
            # Buscamos todos los párrafos dentro del contenido
            paragraphs = content.find_all('p')
            for p in paragraphs:
                text = p.get_text().strip()
                # Limpieza básica de ruido común
                if len(text) > 20 and "publicidad" not in text.lower() and "leer más" not in text.lower():
                    body_parts.append(text)
        
        # Si no encontramos nada con los selectores, intentamos un fallback agresivo
        if not body_parts:
            print("Aviso: No se encontró contenido con los selectores estándar. Intentando fallback...")
            for p in soup.find_all('p'):
                text = p.get_text().strip()
                if len(text) > 40: # Párrafos con cierta sustancia
                    body_parts.append(text)

        # Resultado
        if body_parts:
            print("\n✅ TÍTULO ENCONTRADO:")
            print(f"   {title}")
            print("\n✅ CUERPO ENCONTRADO:")
            full_body = "\n\n".join(body_parts)
            print(full_body)
            print("\n--- Fin de la extracción ---")
        else:
            print("❌ No se pudo extraer el cuerpo de la noticia. Es posible que el muro de pago sea infranqueable para este link.")

    except Exception as e:
        print(f"Error durante el scraping: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Pega el enlace de El Correo: ").strip()
    
    if url.startswith("http"):
        parse_manual_link(url)
    else:
        print("Por favor, introduce una URL válida.")
