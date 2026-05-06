import json
import os
import re
from collections import Counter

def cleanup_news():
    news_file = 'data/news.json'
    if not os.path.exists(news_file):
        print(f"File {news_file} not found.")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news = json.load(f)

    # 1. Build a map of paragraph frequencies for each language field
    fields = ['body', 'body_eu', 'body_pl']
    paragraph_counts = {field: Counter() for field in fields}

    for item in news:
        for field in fields:
            content = item.get(field, '')
            if content:
                paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
                paragraph_counts[field].update(paragraphs)

    # 2. Identify clutter paragraphs (appear in > 1 article and are not too long/short)
    # Also add a static blacklist of common ones we've seen (including translated versions or key words)
    static_blacklist = [
        "nexus, la llave en mano", "nexus, kongresuko", "nexus, rozwiązanie",
        "mercadona",
        "hacienda vigila", "ogasuna ezkontzako", "urząd podatkowy",
        "got talent",
        "un interno de dueñas", "dueñasko preso", "osadzony z dueñas",
        "dos pueblos de cádiz", "cadizko bi herri", "dwa miasta z kadyksu",
        "siete lugares donde antes se fumaba", "zazpi tokitan", "siedem miejsc",
        "jubilados que cobran", "pentsioa jasotzen duten jubilatuak", "emeryci, którzy otrzymują emeryturę",
        "pueden las aerolíneas", "aire konpainiek", "czy linie lotnicze",
        "guardia civil investiga", "guardia zibila ikertzen", "gwardia cywilna",
        "casa de 'alto standing'", "etxea", "dom",
        "mujer recibirá 125.000", "emakume batek", "kobieta otrzyma",
        "aparece primero en gasteiz hoy", "gasteiz hoy", "el correo",
        "primer periódico digital",
        "noticias vitoria-álava",
        "asistencia técnica congresual", "laguntza teknikoaren", "pomocy technicznej",
        "pescadería", "arrandegia", "sprzedawca ryb"
    ]

    cleaned_count = 0
    total_removed = 0

    for item in news:
        item_modified = False
        for field in fields:
            content = item.get(field, '')
            if not content:
                continue
            
            paragraphs = content.split('\n')
            new_paragraphs = []
            
            for p in paragraphs:
                p_strip = p.strip()
                if not p_strip:
                    continue
                
                p_lower = p_strip.lower()
                
                # Check frequency in this specific language
                is_duplicate = paragraph_counts[field][p_strip] > 1
                
                # Check static blacklist
                is_blacklisted = any(b in p_lower for b in static_blacklist)
                
                # Heuristic: if it's a duplicate and looks like a headline (no final dot, or short)
                # Note: some headlines DO have dots in these lists.
                # If it's a duplicate and it's at the end of the list of paragraphs, it's very likely clutter.
                
                # We'll be conservative: if it appears in > 1 article, it's clutter 
                # (unless it's a very common short phrase which we filter by length > 30)
                if (is_duplicate and len(p_strip) > 35 and len(p_strip) < 250) or is_blacklisted:
                    total_removed += 1
                    item_modified = True
                    continue
                
                new_paragraphs.append(p)
            
            if item_modified:
                item[field] = "\n".join(new_paragraphs).strip()
        
        if item_modified:
            cleaned_count += 1

    if cleaned_count > 0:
        with open(news_file, 'w', encoding='utf-8') as f:
            json.dump(news, f, indent=2, ensure_ascii=False)
        print(f"Cleaned {cleaned_count} articles. Removed {total_removed} clutter paragraphs.")
    else:
        print("No articles needed cleaning.")

if __name__ == "__main__":
    cleanup_news()
