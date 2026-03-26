"""
Backfill Euskara translations for existing articles in news.json
that were scraped before the translation feature was added.
"""
import json
import os
import sys
import time

sys.path.append('scraper')
from analyze_sentiment import translate_to_euskara

NEWS_FILE = 'data/news.json'

def run():
    with open(NEWS_FILE, 'r', encoding='utf-8') as f:
        news = json.load(f)

    needs_translation = [n for n in news if not n.get('title_eu') and n.get('lang', 'es') == 'es']
    total = len(needs_translation)
    already_done = len(news) - total

    print(f"Total articles: {len(news)}")
    print(f"Already translated: {already_done}")
    print(f"Needs translation: {total}")

    if total == 0:
        print("Nothing to translate!")
        return

    for i, article in enumerate(news):
        if article.get('title_eu') or article.get('lang') == 'eu':
            continue

        title = article.get('title', '')
        body  = article.get('body', '')
        print(f"[{i+1}/{len(news)}] Translating: {title[:60]}...")

        title_eu, body_eu = translate_to_euskara(title, body)

        if title_eu:
            article['title_eu'] = title_eu
            article['body_eu']  = body_eu
            article['lang'] = 'es'
            print(f"  ✓ {title_eu[:60]}")
        else:
            print(f"  ✗ Failed to translate")

        # Save after each article so progress is not lost on error
        with open(NEWS_FILE, 'w', encoding='utf-8') as f:
            json.dump(news, f, indent=2, ensure_ascii=False)

        # Pause between API calls to stay within rate limits
        time.sleep(2)

    print(f"\nDone! Translated {sum(1 for n in news if n.get('title_eu'))} / {len(news)} articles.")

if __name__ == '__main__':
    run()
