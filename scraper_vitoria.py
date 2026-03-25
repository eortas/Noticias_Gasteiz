import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
import time
import os

def get_vitoria_links():
    """Obtiene todos los enlaces de noticias de la portada de Álava/Araba (Vitoria)."""
    # La URL original de /vitoria/ ahora redirige o da 404. Usamos la sección de Álava.
    url = "https://www.elcorreo.com/alava/araba/"
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
    
    print(f"Obteniendo enlaces desde {url}...")
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        links = []
        # Buscamos enlaces con clases típicas de noticias en El Correo (Vocento)
        # .v-a-link suele ser el enlace principal de la noticia
        for a in soup.select('a.v-a-link, a.v-prp__a, h2 a, h3 a'):
            href = a.get('href')
            if not href:
                continue
                
            # Filtramos para quedarnos con noticias locales y evitar duplicados
            # Las noticias suelen terminar en -nt.html
            if href.endswith(".html") and href not in links:
                # Si queremos filtrar solo Vitoria, buscamos el término en el slug
                if "vitoria" in href.lower() or "/araba/" in href:
                    if not href.startswith("http"):
                        href = f"https://www.elcorreo.com{href}"
                    links.append(href)
        
        # Eliminar duplicados manteniendo el orden
        return list(dict.fromkeys(links))
    except Exception as e:
        print(f"Error al obtener enlaces: {e}")
        return []

def extract_full_data(url):
    """Extrae titular, resumen y cuerpo saltando el muro vía HTML/JSON-LD."""
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 1. Extraer metadatos básicos del JSON-LD (suelen ser correctos para título/fecha)
        metadata = {}
        script_tag = soup.find('script', type='application/ld+json')
        if script_tag:
            try:
                data = json.loads(script_tag.string)
                if isinstance(data, list): data = data[0]
                if "@graph" in data:
                    articles = [item for item in data["@graph"] if item.get("@type") in ["NewsArticle", "Article"]]
                    if articles: data = articles[0]
                
                metadata = {
                    'titulo': data.get('headline'),
                    'resumen': data.get('description'),
                    'fecha': data.get('datePublished')
                }
            except Exception:
                pass

        # 2. Extraer el CUERPO COMPLETO desde el HTML (el JSON-LD suele estar truncado)
        p_tags = soup.select('div.v-p-b p, div.entry-content p, article p')
        
        # Filtramos párrafos vacíos o que sean ruido de suscripción
        blacklist = [
            "Límite de sesiones alcanzadas",
            "acceso al contenido Premium",
            "Por favor, inténtalo pasados unos minutos",
            "Al iniciar sesión desde un dispositivo distinto",
            "Para continuar disfrutando de su suscripción digital",
            "¿Tienes una suscripción?",
            "Inicia sesión",
            "Sesión cerrada",
            "Para continuar leyendo",
            "Suscríbete para leer"
        ]
        
        body_parts = []
        for p in p_tags:
            text = p.get_text().strip()
            # Filtramos si el texto es muy corto o contiene frases de la blacklist
            if text and len(text) > 20: 
                if any(phrase in text for phrase in blacklist):
                    continue
                # Evitar duplicados de texto (a veces se repiten párrafos por lazy loading o estructuras raras)
                if text not in body_parts:
                    body_parts.append(text)
        
        # Opcional: Si el primer párrafo es solo la fecha (que ya tenemos en metadata), lo quitamos
        if body_parts and any(dia in body_parts[0] for dia in ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]):
            if len(body_parts[0]) < 50: # Suele ser una línea corta de fecha
                body_parts.pop(0)

        full_body = "\n\n".join(body_parts)

        # Si el JSON-LD no dio el título/resumen, probamos con meta tags
        if not metadata.get('titulo'):
            metadata['titulo'] = soup.title.string.split("|")[0].strip() if soup.title else ""
        if not metadata.get('resumen'):
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            metadata['resumen'] = meta_desc['content'] if meta_desc else ""

        return {
            'url': url,
            'titulo': metadata.get('titulo'),
            'resumen': metadata.get('resumen'),
            'cuerpo': full_body,
            'fecha': metadata.get('fecha')
        }
    except Exception as e:
        print(f"Error al scrapear {url}: {e}")
        return None

def main():
    # --- Ejecución ---
    links = get_vitoria_links()
    print(f"Detectadas {len(links)} noticias en portada.")

    noticias_list = []
    # Limitamos a las 15 primeras para probar
    limit = 15
    for i, link in enumerate(links[:limit]):
        print(f"[{i+1}/{limit}] Scrapeando: {link}")
        data = extract_full_data(link)
        if data:
            noticias_list.append(data)
        time.sleep(1.5) # Delay prudencial para evitar baneo de IP

    if noticias_list:
        df = pd.DataFrame(noticias_list)
        output_file = "noticias_vitoria.csv"
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\nProceso finalizado. Se han guardado {len(noticias_list)} noticias en '{output_file}'.")
        print("\nPrimeras filas del resultado:")
        print(df[['titulo', 'fecha']].head())
    else:
        print("No se extrajeron noticias.")

if __name__ == "__main__":
    main()
