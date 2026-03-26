import json
import os

news_file = 'data/news.json'
if os.path.exists(news_file):
    with open(news_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total = len(data)
    eu_missing = [x.get('id') for x in data if not x.get('title_eu')]
    pl_missing = [x.get('id') for x in data if not x.get('title_pl')]
    rw_missing = [x.get('id') for x in data if not x.get('body_rw') and not x.get('is_rewritten')]

    print(f"Total articulos: {total}")
    print(f"Euskara missing: {len(eu_missing)}")
    print(f"Polish missing: {len(pl_missing)}")
    print(f"Rewrite missing: {len(rw_missing)}")
    
    if eu_missing:
        print(f"Ejemplos EU missing: {eu_missing[:5]}")
    if pl_missing:
        print(f"Ejemplos PL missing: {pl_missing[:5]}")
else:
    print("No data file found.")
