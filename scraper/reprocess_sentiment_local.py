import json
import os
import sys

# Add scraper path so we can import modules
sys.path.append(os.path.join(os.getcwd(), 'scraper'))

from analyze_sentiment import heuristic_fallback
from update_mood import update_mood_history

def reprocess_sentiment_local():
    news_file = 'data/news.json'
    if not os.path.exists(news_file):
        print("No se encontró data/news.json")
        return

    with open(news_file, 'r', encoding='utf-8') as f:
        news_data = json.load(f)

    updated_count = 0
    total = len(news_data)

    print(f"Reprocesando localmente el sentimiento de {total} artículos...")

    for i, article in enumerate(news_data):
        # We analyze title + body
        title = article.get('original_title') or article.get('title', '')
        body = article.get('original_body') or article.get('body', '')
        text = f"{title}\n\n{body}"

        # Run heuristic fallback
        heur_sentiment, heur_score, heur_category = heuristic_fallback(text)

        # If heuristic has a strong positive/negative rating, we update the score
        if heur_sentiment in ('positiva', 'negativa'):
            old_score = article.get('sentiment')
            new_score = round(heur_score, 4)
            if old_score != new_score:
                article['sentiment'] = new_score
                updated_count += 1
                print(f"[{i+1}/{total}] Actualizado: '{title[:45]}...'")
                print(f"   -> Sentimiento Heurístico: {heur_sentiment} (Score {old_score} -> {new_score})")

    if updated_count > 0:
        with open(news_file, 'w', encoding='utf-8') as f:
            json.dump(news_data, f, indent=2, ensure_ascii=False)
        print(f"\nSe actualizaron {updated_count} artículos.")
        
        # Actualizar el historial de mood
        print("Actualizando historial de 'mood'...")
        update_mood_history()
    else:
        print("\nTodos los artículos ya están al día con la heurística actual.")

if __name__ == "__main__":
    reprocess_sentiment_local()
