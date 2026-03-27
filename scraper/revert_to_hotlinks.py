import json
import os
import urllib.parse

def revert():
    news_file = 'data/news.json'
    if not os.path.exists(news_file):
        return
        
    with open(news_file, 'r', encoding='utf-8') as f:
        news = json.load(f)
        
    for item in news:
        if item.get('image') and item['image'].startswith('data/images/'):
            # Convertir local a Pollinations (como fallback estético)
            title = item.get('title', 'Noticia Vitoria')
            encoded_title = urllib.parse.quote(title)
            item['image'] = f"https://image.pollinations.ai/prompt/{encoded_title}?width=1024&height=1024&nologo=true"
            print(f"Revertido: {item['id']} -> Pollinations")
            
    with open(news_file, 'w', encoding='utf-8') as f:
        json.dump(news, f, indent=2)
    print("Reversión completada.")

if __name__ == "__main__":
    revert()
