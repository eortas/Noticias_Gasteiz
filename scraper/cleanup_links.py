import json
import os

def cleanup_links():
    file_path = 'data/news.json'
    if not os.path.exists(file_path):
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    for item in data:
        for field in ['body', 'body_eu', 'body_pl']:
            if item.get(field):
                lines = item[field].split('\n')
                cleaned = []
                for line in lines:
                    line_lower = line.lower()
                    # Si tiene un enlace de los dominios fuente, lo quitamos
                    if "http" in line_lower and ("gasteizhoy.com" in line_lower or "elcorreo.com" in line_lower):
                        continue
                    cleaned.append(line)
                item[field] = '\n'.join(cleaned)
                
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("Cleaned existing news from promo links.")

if __name__ == "__main__":
    cleanup_links()
