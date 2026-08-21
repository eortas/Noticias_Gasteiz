import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

from analyze_sentiment import analyze_sentiment, get_mistral_sentiment_keys


NEWS_FILE = 'data/news.json'
MODEL_NAME = 'mistral-small-latest'


def parse_date(value):
    """Convierte una fecha ISO a UTC."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def select_recent_news(news, days):
    """Selecciona noticias publicadas durante las últimas horas indicadas."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return [
        item for item in news
        if not str(item.get('id', '')).startswith('resumen_')
        and (parse_date(item.get('date')) or datetime.min.replace(tzinfo=timezone.utc)) >= cutoff
    ]


def build_units(items):
    """Agrupa las fuentes que cuentan el mismo hecho para asignarles un único score."""
    units = {}
    for item in items:
        unit_id = item.get('group_id') or f"item_{item.get('id')}"
        units.setdefault(unit_id, []).append(item)
    return list(units.values())


def build_analysis_text(items):
    """Combina titulares y entradillas de las fuentes relacionadas."""
    parts = []
    for item in items:
        title = item.get('title', '')
        body = item.get('body', '')[:1500]
        parts.append(f"TITULAR: {title}\nTEXTO: {body}")
    return "\n\nOTRA FUENTE DEL MISMO HECHO:\n\n".join(parts)


def save_news(news):
    with open(NEWS_FILE, 'w', encoding='utf-8') as file:
        json.dump(news, file, indent=2, ensure_ascii=False)


def analyze_unit(items):
    text = build_analysis_text(items)
    sentiment, score, category = analyze_sentiment(text, strict=True)
    return items, sentiment, score, category


def run_backfill(days=5, workers=2):
    if len(get_mistral_sentiment_keys()) < 2:
        raise RuntimeError('Se necesitan MISTRAL_VALORACION y MISTRAL_VALORACION2')

    with open(NEWS_FILE, 'r', encoding='utf-8') as file:
        news = json.load(file)

    targets = select_recent_news(news, days)
    units = build_units(targets)
    print(
        f'Backfill Mistral: {len(targets)} noticias de los últimos {days} días '
        f'en {len(units)} hechos distintos.',
        flush=True,
    )

    completed = 0
    failures = []
    updated_at = datetime.now(timezone.utc).isoformat()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(analyze_unit, unit): unit for unit in units}
        for future in as_completed(futures):
            unit = futures[future]
            try:
                items, sentiment, score, category = future.result()
                for item in items:
                    item['sentiment'] = score
                    item['sentiment_label'] = sentiment
                    item['sentiment_model'] = MODEL_NAME
                    item['sentiment_updated_at'] = updated_at
                    item['sentiment_group_verified'] = len(items) > 1
                completed += 1
                print(
                    f'[{completed}/{len(units)}] {sentiment} {score:+.2f} '
                    f'({len(items)} fuente(s)): {items[0].get("title", "")[:70]}',
                    flush=True,
                )
                if completed % 10 == 0:
                    save_news(news)
            except Exception as error:
                failures.append((unit, str(error)))
                print(
                    f'[ERROR] {unit[0].get("title", "")[:70]}: {error}',
                    flush=True,
                )

    save_news(news)
    print(
        f'Backfill terminado: {completed} hechos actualizados y {len(failures)} fallidos.',
        flush=True,
    )
    return failures


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=5)
    parser.add_argument('--workers', type=int, default=2)
    args = parser.parse_args()

    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    failed = run_backfill(days=args.days, workers=args.workers)
    raise SystemExit(1 if failed else 0)
