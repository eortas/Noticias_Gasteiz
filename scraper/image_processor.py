import os
import requests
import io
import time
from PIL import Image
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

load_dotenv()

# Configuración del Cliente
HF_TOKEN = os.getenv("HF_TOKEN")
client = InferenceClient(api_key=HF_TOKEN)

def download_image_pil(url):
    """Downloads an image and returns a PIL Image object."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return Image.open(io.BytesIO(response.content)).convert("RGB")
        else:
            print(f"Failed to download image: {url} (Status: {response.status_code})")
    except Exception as e:
        print(f"Error downloading image {url}: {e}")
    return None

def process_and_save_image(url_original, article_id, prompt_texto, output_dir='data/images'):
    """
    Toma la imagen original del periódico y la transforma en una versión artística
    usando img2img de Hugging Face InferenceClient.
    """
    os.makedirs(output_dir, exist_ok=True)
    local_filename = f"{article_id}.jpg"
    local_path = os.path.join(output_dir, local_filename)

    if not url_original:
        print(f"No hay URL original para {article_id}. Generando desde cero (t2i)...")
        return generate_t2i_fallback(prompt_texto, article_id, output_dir)

    try:
        # Descargar imagen original
        img_original = download_image_pil(url_original)
        if not img_original:
            return generate_t2i_fallback(prompt_texto, article_id, output_dir)
        
        # Redimensionar a 512x512 para evitar timeouts y ser eficiente
        img_original.thumbnail((512, 512))
        
        print(f"  Iniciando re-interpretación IA para {article_id}...")
        
        # Intentar img2img con InferenceClient
        # El tier gratuito a veces da 503 (modelo cargando), reintentamos una vez
        img_generada = None
        for attempt in range(2):
            try:
                img_generada = client.image_to_image(
                    image=img_original,
                    prompt=f"Cinematic news illustration about {prompt_texto}. Professional artistic style, high quality, vibrant colors, no text, documentary style.",
                    model="runwayml/stable-diffusion-v1-5", # SD 1.5 es estable y rápido
                    strength=0.5,
                    guidance_scale=7.5
                )
                if img_generada:
                    break
            except Exception as e:
                if "503" in str(e) and attempt == 0:
                    print("  Modelo cargando (503), esperando 5s...")
                    time.sleep(5)
                    continue
                raise e

        if img_generada:
            img_generada.save(local_path, format='JPEG', quality=85)
            print(f"  ✓ Imagen procesada y guardada: {local_path}")
            return f"data/images/{local_filename}"

    except Exception as e:
        print(f"  ! Error en el pipeline img2img: {e}")
    
    # Si falla img2img, intentar texto a imagen (t2i) como último recurso
    return generate_t2i_fallback(prompt_texto, article_id, output_dir)

def generate_t2i_fallback(prompt_texto, article_id, output_dir='data/images'):
    """Generación de texto a imagen si img2img falla (incluyendo errores 402)."""
    local_path = os.path.join(output_dir, f"{article_id}.jpg")
    print(f"  Usando fallback Texto-a-Imagen para {article_id}...")
    
    # 1. Intentar HF Texto-a-Imagen
    try:
        img_generada = client.text_to_image(
            prompt=f"Professional news illustration: {prompt_texto}. Artistic, realistic photography style, cinematic lighting, 8k, no text.",
            model="stabilityai/stable-diffusion-xl-base-1.0"
        )
        if img_generada:
            img_generada.save(local_path, format='JPEG', quality=85)
            print(f"  ✓ Imagen generada (t2i HF) y guardada: {local_path}")
            return f"data/images/{article_id}.jpg"
    except Exception as e:
        print(f"  ! Fallo en HF t2i: {e}")
        if "402" in str(e):
            print("  [402 Payment Required] Créditos agotados en HF. Usando Pollinations...")

    # 2. Fallback final CRÍTICO: Pollinations.ai (Sin tokens, siempre disponible)
    print(f"  [CRITICAL FALLBACK] Usando Pollinations.ai para {article_id}...")
    try:
        import urllib.parse
        encoded_prompt = urllib.parse.quote(f"Vitoria news: {prompt_texto}, professional photography, cinematic, documentary style")
        pollinations_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&seed={article_id}"
        
        response = requests.get(pollinations_url, timeout=30)
        if response.status_code == 200:
            with open(local_path, 'wb') as f:
                f.write(response.content)
            print(f"  ✓ Imagen descargada de Pollinations: {local_path}")
            return f"data/images/{article_id}.jpg"
        else:
            print(f"  !! Pollinations también falló ({response.status_code})")
    except Exception as e:
        print(f"  !! Error conectando con Pollinations: {e}")
    
    return None
