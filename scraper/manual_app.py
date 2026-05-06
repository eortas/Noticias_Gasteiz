import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import time

# Configuración de la página
st.set_page_config(page_title="Extractor de El Correo", page_icon="📰", layout="centered")

# Estilos personalizados para mejorar la lectura
st.markdown("""
    <style>
    .main .block-container {
        max-width: 800px;
        padding-top: 2rem;
    }
    .stMarkdown p {
        font-size: 1.4rem !important;
        line-height: 1.6 !important;
        color: #333;
    }
    h1 {
        font-size: 2.5rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📰 Extractor de El Correo")

# Función de extracción (la misma que manual_parse.py pero adaptada a Streamlit)
def extract_content(url):
    blacklist = [
        "este vídeo es exclusivo para suscriptores",
        "disfruta de acceso ilimitado",
        "¿ya tienes una suscripción?",
        "inicia sesión",
        "hazte suscriptor",
        "registrado",
        "más información"
    ]
    
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
        'Referer': 'https://www.google.com/'
    }

    try:
        with st.spinner("Extrayendo contenido..."):
            response = scraper.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                return None, f"Error: Código de estado {response.status_code}"

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Título
            title = "Sin título"
            title_tag = soup.find('h1')
            if title_tag:
                title = title_tag.get_text().strip()
            elif soup.title:
                title = soup.title.string

            # Cuerpo
            body_parts = []
            content = soup.find('div', class_='v-p-b') or \
                      soup.find('div', class_='entry-content') or \
                      soup.find('article') or \
                      soup.find('div', class_='voc-story')
            
            if content:
                for p in content.find_all('p'):
                    text = p.get_text().strip()
                    text_lower = text.lower()
                    if not any(phrase in text_lower for phrase in blacklist) and len(text) > 20 and "publicidad" not in text_lower:
                        body_parts.append(text)
            
            if not body_parts:
                for p in soup.find_all('p'):
                    text = p.get_text().strip()
                    if len(text) > 45:
                        body_parts.append(text)

            return title, body_parts
    except Exception as e:
        return None, str(e)

# Interfaz de usuario
url_input = st.text_input("Introduce la URL de la noticia:", placeholder="https://www.elcorreo.com/...")

if st.button("Extraer Noticia") or url_input:
    if url_input.startswith("http"):
        title, body = extract_content(url_input)
        
        if title:
            st.success("¡Noticia extraída con éxito!")
            st.header(title)
            st.divider()
            
            if body:
                for p in body:
                    st.write(p)
                
                # Botón para copiar todo el texto
                full_text = "\n\n".join(body)
                st.download_button("Descargar como Texto", full_text, file_name="noticia.txt")
            else:
                st.warning("No se pudo extraer el cuerpo de la noticia.")
        else:
            st.error(f"No se pudo extraer la noticia. Detalle: {body}")
    elif url_input:
        st.error("Por favor, introduce una URL válida.")
