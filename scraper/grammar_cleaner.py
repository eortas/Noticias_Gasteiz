import re
import os
import json

def fix_grammar_errors(text):
    """
    Corregimos errores gramaticales comunes generados por modelos de lenguaje (LLMs)
    en español, como la conjugación incorrecta de verbos diptongados o términos no estándar.
    """
    if not text:
        return text

    # Lista de patrones regex y sus reemplazos correctos en castellano
    replacements = [
        # Verbo volcar: "se volca" -> "se vuelca", "volca" -> "vuelca"
        (r'\b([Ss]e)\s+volca\b', r'\1 vuelca'),
        (r'\b([Ss]e)\s+volcan\b', r'\1 vuelcan'),
        (r'\bvolca\b', 'vuelca'),
        (r'\bVolca\b', 'Vuelca'),

        # Sustantivo "volcamiento" -> "vuelco" (estándar en España)
        (r'\bvolcamiento\b', 'vuelco'),
        (r'\bVolcamiento\b', 'Vuelco'),
        (r'\bvolcamientos\b', 'vuelcos'),
        (r'\bVolcamientos\b', 'Vuelcos'),

        # Verbo forzar: "se forza" -> "se fuerza"
        (r'\b([Ss]e)\s+forza\b', r'\1 fuerza'),
        (r'\b([Ss]e)\s+forzan\b', r'\1 fuerzan'),

        # Verbo colgar: "se colga" -> "se cuelga"
        (r'\b([Ss]e)\s+colga\b', r'\1 cuelga'),
        (r'\b([Ss]e)\s+colgan\b', r'\1 cuelgan'),

        # Verbo apretar: "se apreta" -> "se aprieta"
        (r'\b([Ss]e)\s+apreta\b', r'\1 aprieta'),
        (r'\b([Ss]e)\s+apretan\b', r'\1 aprietan'),

        # Verbo soltar: "se solta" -> "se suelta"
        (r'\b([Ss]e)\s+solta\b', r'\1 suelta'),
        (r'\b([Ss]e)\s+soltan\b', r'\1 sueltan'),

        # Verbo renovar: "se renova" -> "se renueva"
        (r'\b([Ss]e)\s+renova\b', r'\1 renueva'),
        (r'\b([Ss]e)\s+renovan\b', r'\1 renuevan')
    ]

    cleaned = text
    for pattern, repl in replacements:
        cleaned = re.sub(pattern, repl, cleaned)

    return cleaned

def fix_grammar_in_news_json(filepath='data/news.json'):
    """
    Recorremos el archivo JSON de noticias y corregimos las palabras o expresiones
    incorrectas en títulos, cuerpos y resúmenes.
    """
    if not os.path.exists(filepath):
        print(f"No se encontró el archivo {filepath}")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        news = json.load(f)

    changes_count = 0
    fields_to_clean = ['title', 'body', 'original_title', 'original_body', 'summary']

    for item in news:
        for field in fields_to_clean:
            if field in item and item[field]:
                original_text = item[field]
                corrected_text = fix_grammar_errors(original_text)
                if original_text != corrected_text:
                    item[field] = corrected_text
                    changes_count += 1

    if changes_count > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(news, f, indent=2, ensure_ascii=False)
        print(f"[OK] Se han corregido {changes_count} textos con errores gramaticales en {filepath}.")
    else:
        print(f"[OK] No se detectaron errores gramaticales pendientes en {filepath}.")

if __name__ == '__main__':
    fix_grammar_in_news_json()
