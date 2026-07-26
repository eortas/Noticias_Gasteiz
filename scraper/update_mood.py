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

    # 1. Agrupar sentimientos por fecha (YYYY-MM-DD) y sección
    # Secciones válidas: economia, sociedad, deportes, cultura. 'alava' es el global del día.
    valid_sections = ['economia', 'sociedad', 'deportes', 'cultura']
    daily_scores = {sec: {} for sec in ['alava'] + valid_sections}
    
    for item in news:
        if item.get('is_summary'):
            continue
            
        date_str = item.get('date', '')
        if not date_str or len(date_str) < 10:
            continue
            
        day = date_str[:10]
        
        try:
            score = float(item.get('sentiment', 0))
        except (ValueError, TypeError):
            continue

        # 'alava' representa el estado de ánimo global (todas las noticias del día)
        if day not in daily_scores['alava']:
            daily_scores['alava'][day] = []
        daily_scores['alava'][day].append(score)

        # Agrupamos también en su sección correspondiente si es válida
        section = item.get('source_section')
        if section in valid_sections:
            if day not in daily_scores[section]:
                daily_scores[section][day] = []
            daily_scores[section][day].append(score)

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

    # 3. Fusionar las puntuaciones respetando la inmutabilidad de días pasados
    today_str = datetime.now().strftime('%Y-%m-%d')

    for sec in history_dict.keys():
        for day, scores in daily_scores[sec].items():
            if not scores:
                continue

            # Si el día es pasado y ya se guardó en el historial, mantenemos su valor persistido
            if day < today_str and day in history_dict[sec]:
                continue

            # Calculamos o actualizamos la nota media solo para el día de hoy (o días no registrados)
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
