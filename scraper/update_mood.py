import json
import os
from datetime import datetime

def update_mood_history():
    news_file = 'data/news.json'
    mood_file = 'data/mood_history.json'
    
    if not os.path.exists(news_file):
        print("No se encontró news.json")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news = json.load(f)

    # Agrupar sentimientos por fecha (YYYY-MM-DD)
    daily_scores = {}
    for item in news:
        date_str = item.get('date', '')
        try:
            # Extraer solo la parte de la fecha YYYY-MM-DD
            day = date_str[:10]
            score = float(item.get('sentiment', 0))
            
            if day not in daily_scores:
                daily_scores[day] = []
            daily_scores[day].append(score)
        except (ValueError, TypeError):
            continue

    # Cargar historial existente para no perder datos antiguos que ya no están en news.json
    history_dict = {}
    if os.path.exists(mood_file):
        try:
            with open(mood_file, 'r', encoding='utf-8') as f:
                old_history = json.load(f)
                for entry in old_history:
                    history_dict[entry['date']] = entry['score']
        except:
            pass

    # Fusionar con los datos calculados hoy
    for day, scores in daily_scores.items():
        avg_score = sum(scores) / len(scores)
        history_dict[day] = round(avg_score, 2)

    # Convertir a lista ordenada
    final_history = []
    for day in sorted(history_dict.keys()):
        final_history.append({
            "date": day,
            "score": history_dict[day]
        })

    with open(mood_file, 'w', encoding='utf-8') as f:
        json.dump(final_history, f, indent=2, ensure_ascii=False)
    
    print(f"Historial de 'Mood' actualizado. Total acumulado: {len(final_history)} días.")

if __name__ == "__main__":
    update_mood_history()
