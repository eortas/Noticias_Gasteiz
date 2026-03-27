import os
import requests
import json
import time
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
# Stable Diffusion 2.1 supports img2img well in the Inference API
API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2-1"
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}

def download_image_pil(url):
    """Downloads an image and returns a PIL Image object."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content)).convert("RGB")
        else:
            print(f"Failed to download image: {url} (Status: {response.status_code})")
    except Exception as e:
        print(f"Error downloading image {url}: {e}")
    return None

# global session for connection pooling
session = requests.Session()

def reinterpret_image(image_pil, context_text, strength=0.6, max_retries=3):
    """
    Transforms an existing PIL image using img2img with multi-model fallback.
    Optimized for stability with smaller payloads and multiple model options.
    """
    if not HF_TOKEN:
        print("HF_TOKEN missing. Skipping img2img.")
        return None

    # Resize to 768x768 to reduce payload size and IncompleteRead errors
    image_pil.thumbnail((768, 768))
    
    img_byte_arr = BytesIO()
    image_pil.save(img_byte_arr, format='JPEG', quality=75)
    img_bytes = img_byte_arr.getvalue()

    # Optimize prompt based on user's faithful reimagining strategy
    prompt = f"Professional news photography, Vitoria-Gasteiz, preserving composition of input, scene about: {context_text}. High realistic detail, photojournalism style."
    
    # Models to try in sequence - SDXL is now primary for better realism
    models = [
        "stabilityai/stable-diffusion-xl-base-1.0",
        "stabilityai/stable-diffusion-2-1",
        "runwayml/stable-diffusion-v1-5"
    ]
    
    for attempt in range(max_retries):
        model = models[attempt % len(models)]
        api_url = f"https://api-inference.huggingface.co/models/{model}"
        
        try:
            files = {
                "image": ("image.jpg", img_bytes, "image/jpeg")
            }
            # Custom parameters for news fidelity
            params = {
                "strength": 0.45,       # "Punto Dulce" for structural fidelity
                "guidance_scale": 8.0,  # Strict adherence to contextual prompt
                "num_inference_steps": 30 # High detail for professional look
            }
            
            data = {
                "inputs": prompt,
                "parameters": json.dumps(params)
            }
            
            print(f"Attempting img2img with {model} (Attempt {attempt+1}/{max_retries})...")
            
            headers = HEADERS.copy()
            headers['Connection'] = 'close'
            
            response = session.post(api_url, headers=headers, files=files, data=data, timeout=60)
            
            if response.status_code == 200:
                if response.headers.get('Content-Type', '').startswith('image/'):
                    return Image.open(BytesIO(response.content))
                else:
                    print(f"HF returned non-image content: {response.text[:100]}")
            
            elif response.status_code == 503:
                wait_time = (attempt + 1) * 10
                print(f"Model {model} loading. Waiting {wait_time}s...")
                time.sleep(wait_time)
            
            elif response.status_code == 429:
                print("Rate limit (429). Waiting 30s...")
                time.sleep(30)
            
            else:
                print(f"HF API Error ({model}): {response.status_code}")
        
        except (requests.exceptions.RequestException, Exception) as e:
            print(f"Network error ({model}): {e}")
            time.sleep(5)
    
    return None

import urllib.parse

def generate_hf_image(title, article_id, output_dir='data/images'):
    """
    Generates a new image from scratch using HF Inference API or Pollinations fallback.
    Used when img2img transformation is not possible or fails.
    """
    file_path = os.path.join(output_dir, f"{article_id}.jpg")
    
    # Models for text-to-image
    models = [
        "black-forest-labs/FLUX.1-schnell",
        "stabilityai/stable-diffusion-xl-base-1.0",
        "runwayml/stable-diffusion-v1-5"
    ]
    
    prompt = f"Professional news photography from Vitoria-Gasteiz: {title}. Realistic, high quality."
    
    for model in models:
        api_url = f"https://api-inference.huggingface.co/models/{model}"
        print(f"  Trying HF Text-to-Image with {model}...")
        try:
            response = session.post(api_url, headers=HEADERS, json={"inputs": prompt}, timeout=30)
            if response.status_code == 200:
                content = response.content
                valid_magic = len(content) > 2 and ((content[0] == 0xFF and content[1] == 0xD8) or (content[0] == 0x89 and content[1] == 0x50))
                if valid_magic:
                    with open(file_path, 'wb') as f:
                        f.write(content)
                    print(f"Generated image saved locally: {file_path}")
                    return f"data/images/{article_id}.jpg"
            elif response.status_code == 503:
                print(f"  Model {model} loading, skipping...")
            else:
                print(f"  Failed: {response.status_code}")
        except Exception as e:
            print(f"  Error with {model}: {e}")
            
    print(f"All HF models failed for {article_id}. Falling back to Pollinations API...")
    import urllib.parse
    encoded_prompt = urllib.parse.quote(f"Vitoria news: {title}, realistic photography, cinematic")
    
    pollinations_key = os.getenv("POLLINATIONS_KEY")
    if pollinations_key:
        pollinations_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&key={pollinations_key}"
    else:
        pollinations_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
        print("Warning: POLLINATIONS_KEY not found in .env. Pollinations may return 401.")
        
    req_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
        
    try:
        response = session.get(pollinations_url, headers=req_headers, timeout=40)
        if response.status_code == 200:
            content = response.content
            valid_magic = len(content) > 2 and ((content[0] == 0xFF and content[1] == 0xD8) or (content[0] == 0x89 and content[1] == 0x50))
            if valid_magic and len(content) > 10000:
                with open(file_path, 'wb') as f:
                    f.write(content)
                print(f"Fallback image saved from Pollinations: {file_path}")
                return f"data/images/{article_id}.jpg"
            else:
                print(f"  [Error] Pollinations returned invalid image or HTML.")
        else:
            print(f"  [Error] Pollinations failed ({response.status_code}): {response.text[:100]}")
    except Exception as e:
        print(f"  [Error] Failed to connect to Pollinations: {e}")
        
    return None

def process_and_save_image(url, article_id, context_text, output_dir='data/images'):
    """
    Full workflow: Download -> Reinterpret -> Save.
    If transformation fails, falls back to text-to-image generation.
    Returns the local path or URL.
    """
    os.makedirs(output_dir, exist_ok=True)
    local_filename = f"{article_id}.jpg"
    local_path = os.path.join(output_dir, local_filename)
    
    # 1. Try img2img if we have a source URL
    if url:
        original_pil = download_image_pil(url)
        if original_pil:
            reimagined_pil = reinterpret_image(original_pil, context_text)
            if reimagined_pil:
                reimagined_pil.save(local_path, format='JPEG', quality=85)
                print(f"Image reimagined and saved: {local_path}")
                return f"data/images/{local_filename}"
    
    # 2. Fallback to Text-to-Image if img2img failed or no original
    print(f"img2img failed/skipped for {article_id}. Using t2i fallback.")
    return generate_hf_image(context_text, article_id, output_dir)
