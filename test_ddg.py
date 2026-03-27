import os
import requests
import re
import json

def test_ddg(query):
    print(f"Buscando imagen real en DDG para: {query}")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    
    # 1. Obtener el token vqd
    search_url = "https://duckduckgo.com/"
    res = requests.get(search_url, params={"q": query}, headers=headers, timeout=10)
    vqd = re.search(r'vqd=([\d-]+)&', res.text)
    if not vqd:
        vqd = re.search(r'vqd=["\']([\d-]+)["\']', res.text)
    
    if vqd:
        vqd_token = vqd.group(1)
        print(f"Token VQD: {vqd_token}")
        # 2. Llamar a la API interna de imágenes de DDG
        img_api_url = "https://duckduckgo.com/i.js"
        params = {
            "q": query,
            "o": "json",
            "vqd": vqd_token,
            "f": ",,,",
            "p": "1"
        }
        res = requests.get(img_api_url, params=params, headers=headers, timeout=10)
        data = res.json()
        if data.get("results"):
            img_url = data["results"][0]["image"]
            print(f"Resultado: {img_url}")
            return img_url
            
    print("No se pudo encontrar imagen en DDG.")
    return None

if __name__ == "__main__":
    test_ddg("Vitoria-Gasteiz virgen blanca")
