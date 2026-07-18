import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def create_summary_image(text, output_path):
    # Dimensiones 16:9 premium
    width = 1200
    height = 675
    
    # 1. Crear lienzo base con color oscuro de fondo (Slate-950)
    img = Image.new("RGBA", (width, height), (15, 23, 42, 255))
    draw = ImageDraw.Draw(img)
    
    # 2. Dibujar un degradado lineal suave
    # De un tono índigo oscuro a un pizarra oscuro
    color_start = (30, 27, 75)   # #1e1b4b (índigo oscuro)
    color_end = (15, 23, 42)     # #0f172a (pizarra oscuro)
    
    for y in range(height):
        # Interpolación lineal simple
        factor = y / height
        r = int(color_start[0] + (color_end[0] - color_start[0]) * factor)
        g = int(color_start[1] + (color_end[1] - color_start[1]) * factor)
        b = int(color_start[2] + (color_end[2] - color_start[2]) * factor)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
        
    # 3. Añadir círculos de brillo difuminados (glow orbs) para estética premium
    glow_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    
    # Orbe 1: Índigo / Púrpura en la esquina superior izquierda
    glow_draw.ellipse([(-100, -100), (500, 500)], fill=(99, 102, 241, 45))
    
    # Orbe 2: Esmeralda en la esquina inferior derecha
    glow_draw.ellipse([(800, 300), (1300, 800)], fill=(16, 185, 129, 35))
    
    # Aplicar desenfoque gaussiano fuerte para suavizar los orbes
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(80))
    img = Image.alpha_composite(img, glow_layer)
    
    # 4. Cargar tipografía de Windows (Segoe UI Bold para diseño moderno)
    font_paths = [
        "C:\\Windows\\Fonts\\segoeuib.ttf",  # Segoe UI Bold (Ideal en Windows)
        "C:\\Windows\\Fonts\\arialbd.ttf",   # Arial Bold
        "C:\\Windows\\Fonts\\calibrib.ttf",   # Calibri Bold
    ]
    
    font = None
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                # Tamaño de fuente premium grande y legible
                font = ImageFont.truetype(fp, 52)
                break
            except:
                continue
                
    if font is None:
        font = ImageFont.load_default()
        print("Aviso: Usando fuente por defecto porque no se encontró ninguna TTF compatible.")

    # 5. Dibujar texto en el centro (solo el texto principal, sin subtexto)
    draw = ImageDraw.Draw(img)
    
    # Obtener el cuadro delimitador del texto para centrado absoluto
    # Soporta tanto pillow nuevo (getbbox) como anterior
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
    except AttributeError:
        # Fallback para versiones antiguas de PIL
        text_w, text_h = draw.textsize(text, font=font)
        
    x = (width - text_w) // 2
    y = (height - text_h) // 2 - 15  # Ajuste estético leve hacia arriba
    
    # Dibujar sombra sutil para contraste premium
    draw.text((x + 3, y + 3), text, fill=(0, 0, 0, 90), font=font)
    
    # Dibujar texto principal en blanco
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
    
    # Asegurar el directorio de destino
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Guardar en formato PNG optimizado
    img.convert("RGB").save(output_path, "PNG", optimize=True)
    print(f"Imagen generada con éxito en: {output_path}")

def generate_all_summaries():
    # Textos localizados proporcionados por el usuario
    languages = {
        "es": "Resumen de noticias del día",
        "eu": "Eguneko albisteen laburpena",
        "fr": "Résumé de l'actualité du jour",
        "en": "Daily news summary",
        "pl": "Podsumowanie wiadomości dnia"
    }
    
    for lang, text in languages.items():
        output_file = f"data/resumen_{lang}.png"
        create_summary_image(text, output_file)

if __name__ == "__main__":
    generate_all_summaries()
