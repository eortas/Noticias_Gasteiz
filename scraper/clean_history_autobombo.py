import json
import os
import re

def clean_history_autobombo():
    news_file = 'data/news.json'
    if not os.path.exists(news_file):
        print(f"No se encontró {news_file}")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news = json.load(f)

    # Frases a buscar y eliminar (variaciones detectadas)
    patterns = [
        r"En Gasteiz Hoy.*", # Regla general agresiva
        r"Ocio en Vitoria, Turismo Vitoria, Obras de Vitoria.*",
        r"Periodismo ciudadano e independiente para lectores alaveses.*",
        r"Gasteiz Hoy, todos los derechos reservados.*",
        r"ofreciendo a nuestros lectores una visión completa de la ciudad y sus barrios.*",
        r"noticias sobre ocio, turismo, obras y tráfico en la región.*",
        r"Sigue la actualidad de Vitoria-Gasteiz y Álava en Gasteiz Hoy.*",
        r"El primer periódico digital de Vitoria-Gasteiz sobre la ciudad.*",
        r"En el corazón de la ciudad, Gasteiz Hoy se erige.*",
        r"ofreciendo una visión integral de la actualidad local.*",
        r"fuente confiable para los ciudadanos de Vitoria-Gasteiz.*",
        r"enfoque de periodismo ciudadano e independiente.*",
        r"lectores alaveses que buscan una cobertura informativa rigurosa.*",
        r"Todos los derechos reservados\."
    ]

    count = 0
    for item in news:
        changed = False
        for field in ['body', 'original_body']:
            if item.get(field):
                original_text = item[field]
                new_text = original_text
                
                # Regla de los patrones específicos
                for pattern in patterns:
                    new_text = re.sub(r'\s*' + pattern, '', new_text, flags=re.IGNORECASE | re.DOTALL)
                
                # Nueva Regla del Usuario: si el último párrafo contiene "Gasteiz Hoy", se elimina
                paragraphs = new_text.split('\n\n')
                if paragraphs:
                    last_p = paragraphs[-1].strip().lower()
                    if "gasteiz hoy" in last_p:
                        paragraphs.pop()
                        new_text = '\n\n'.join(paragraphs).strip()

                if new_text != original_text:
                    item[field] = new_text.strip()
                    changed = True
        
        if changed:
            count += 1

    if count > 0:
        with open(news_file, 'w', encoding='utf-8') as f:
            json.dump(news, f, indent=2, ensure_ascii=False)
        print(f"Limpieza completada. Se han limpiado {count} noticias de autobombo.")
    else:
        print("No se encontraron noticias con los patrones de autobombo especificados.")

if __name__ == "__main__":
    clean_history_autobombo()
