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

    # 1. Agrupar sentimientos por sección y fecha (YYYY-MM-DD)
    # Secciones válidas: economia, sociedad, deportes, cultura. El resto va a 'alava' (All)
    valid_sections = ['economia', 'sociedad', 'deportes', 'cultura']
    daily_scores = {sec: {} for sec in ['alava'] + valid_sections}
    
    for item in news:
        if item.get('is_summary'):
            continue
            
        section = item.get('source_section')
        if section not in valid_sections:
            section = 'alava'
            
        date_str = item.get('date', '')
        try:
            day = date_str[:10]
            score = float(item.get('sentiment', 0))
            
            if day not in daily_scores[section]:
                daily_scores[section][day] = []
            daily_scores[section][day].append(score)
        except (ValueError, TypeError):
            continue

    # 2. Cargar historial existente y migrar si es necesario
    history_dict = {sec: {} for sec in ['alava'] + valid_sections}
    if os.path.exists(mood_file):
        try:
            with open(mood_file, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                
                # Caso A: El archivo antiguo era una lista plana (solo para 'alava')
                if isinstance(old_data, list):
                    print("    [MIGRACIÓN] Convirtiendo historial de Mood plano al nuevo formato estructurado por secciones...")
                    for entry in old_data:
                        history_dict['alava'][entry['date']] = entry['score']
                # Caso B: El archivo ya tiene el nuevo formato de diccionario
                elif isinstance(old_data, dict):
                    for sec in history_dict.keys():
                        if sec in old_data:
                            for entry in old_data[sec]:
                                history_dict[sec][entry['date']] = entry['score']
        except Exception as e:
            print(f"    [AVISO] No se pudo cargar el historial anterior de Mood: {e}")

    # 3. Fusionar con las puntuaciones calculadas hoy
    for sec in history_dict.keys():
        for day, scores in daily_scores[sec].items():
            if scores:
                avg_score = sum(scores) / len(scores)
                history_dict[sec][day] = round(avg_score, 2)

    # 4. Convertir a listas ordenadas cronológicamente
    final_history = {}
    for sec in history_dict.keys():
        sec_list = []
        for day in sorted(history_dict[sec].keys()):
            sec_list.append({
                "date": day,
                "score": history_dict[sec][day]
            })
        final_history[sec] = sec_list

    with open(mood_file, 'w', encoding='utf-8') as f:
        json.dump(final_history, f, indent=2, ensure_ascii=False)
    
    print(f"Historial de 'Mood' por secciones actualizado correctamente en {mood_file}.")

if __name__ == "__main__":
    update_mood_history()
