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

def reinterpret_image(image_pil, context_text, strength=0.5, max_retries=2):
    """
    Transforms an existing PIL image into a derivative work.
    Pipeline:
      1. HF router img2img (runwayml/SD-v1-5) — dual token
      2. OpenCV illustration filter (free, local, always works)
    """
    import base64, io as _io

    # Resize for HF compatibility
    img_copy = image_pil.copy()
    img_copy.thumbnail((768, 768), Image.Resampling.LANCZOS)
    buf = _io.BytesIO()
    img_copy.save(buf, format='JPEG', quality=80)
    img_b64 = base64.b64encode(buf.getvalue()).decode()

    prompt = f"Professional news photography of Vitoria-Gasteiz: {context_text}. Photorealistic, high quality."

    # --- Layer 1: HF Router img2img ---
    hf_tokens = [t for t in [os.getenv("HF_TOKEN"), os.getenv("HF2_TOKEN")] if t]
    hf_models = [
        "runwayml/stable-diffusion-v1-5",
        "stabilityai/stable-diffusion-xl-base-1.0",
    ]
    for token in hf_tokens:
        headers = {"Authorization": f"Bearer {token}"}
        for model in hf_models:
            url = f"https://router.huggingface.co/hf-inference/models/{model}/image-to-image"
            payload = {
                "inputs": img_b64,
                "parameters": {
                    "prompt": prompt,
                    "strength": strength,
                    "guidance_scale": 8.0
                }
            }
            try:
                print(f"  HF img2img ({model[:30]}..., token {token[:6]}...)...")
                resp = session.post(url, headers=headers, json=payload, timeout=45)
                if resp.status_code == 200 and resp.headers.get("Content-Type", "").startswith("image/"):
                    result = Image.open(_io.BytesIO(resp.content)).convert("RGB")
                    print(f"  ✓ HF img2img success!")
                    return result
                elif resp.status_code == 503:
                    print(f"  Model loading (503), skipping...")
                elif resp.status_code == 429:
                    print(f"  Rate limit (429) for token {token[:6]}, trying next token...")
                    break
                else:
                    print(f"  HF img2img failed: {resp.status_code} {resp.text[:80]}")
            except Exception as e:
                print(f"  HF img2img error: {e}")

    # --- Layer 2: OpenCV Illustration Filter (always available) ---
    print(f"  Falling back to OpenCV illustration filter...")
    try:
        import cv2
        import numpy as np

        # Crop/resize to 1024x1024
        target = 1024
        w, h = image_pil.size
        aspect = w / h
        if aspect > 1:
            new_w = int(target * aspect)
            image_pil = image_pil.resize((new_w, target), Image.Resampling.LANCZOS)
            left = (image_pil.width - target) // 2
            image_pil = image_pil.crop((left, 0, left + target, target))
        else:
            new_h = int(target / aspect)
            image_pil = image_pil.resize((target, new_h), Image.Resampling.LANCZOS)
            top = (image_pil.height - target) // 2
            image_pil = image_pil.crop((0, top, target, top + target))

        img = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)

        # Edge mask (comic lines)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, 7)
        edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 2)

        # Painted color (bilateral filter × 3)
        color = img.copy()
        for _ in range(3):
            color = cv2.bilateralFilter(color, d=9, sigmaColor=250, sigmaSpace=250)

        # Boost saturation
        hsv = cv2.cvtColor(color, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.3, 0, 255)
        color = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        # Combine edges + color
        cartoon = cv2.bitwise_and(color, color, mask=edges)
        cartoon_rgb = cv2.cvtColor(cartoon, cv2.COLOR_BGR2RGB)
        print(f"  ✓ OpenCV illustration applied.")
        return Image.fromarray(cartoon_rgb)

    except Exception as e:
        print(f"  OpenCV filter failed: {e}")

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
    
    hf_tokens = [t for t in [os.getenv("HF_TOKEN"), os.getenv("HF2_TOKEN")] if t]
    if not hf_tokens:
        print("No HF tokens available.")
        
    for token in hf_tokens:
        token_headers = {"Authorization": f"Bearer {token}"}
        for model in models:
            api_url = f"https://api-inference.huggingface.co/models/{model}"
            print(f"  Trying HF Text-to-Image with {model} (Token {token[:6]}...)...")
            try:
                response = session.post(api_url, headers=token_headers, json={"inputs": prompt}, timeout=30)
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
            
    print(f"All HF models and tokens failed for {article_id}. Falling back to Pollinations API...")
    import urllib.parse
    encoded_prompt = urllib.parse.quote(f"Vitoria news: {title}, realistic photography, cinematic")
    
    pollinations_key = os.getenv("POLLINATIONS_KEY")
    if pollinations_key:
        pollinations_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&model=flux&key={pollinations_key}"
    else:
        pollinations_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&model=flux"
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
