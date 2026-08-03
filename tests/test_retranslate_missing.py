import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path


# Evitamos cargar el cliente externo porque esta prueba no realiza traducciones.
fake_analyze_sentiment = types.ModuleType('analyze_sentiment')
fake_analyze_sentiment.translate_article = lambda *args, **kwargs: ('', '')
sys.modules['analyze_sentiment'] = fake_analyze_sentiment

module_path = Path(__file__).resolve().parents[1] / 'scraper' / 'retranslate_missing.py'
module_spec = importlib.util.spec_from_file_location('retranslate_missing', module_path)
retranslate_missing = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(retranslate_missing)


class RetranslateMissingTests(unittest.TestCase):
    def test_ignores_news_with_null_date(self):
        news = [{'date': None, 'title': 'Noticia sin fecha'}]

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / 'data'
            data_dir.mkdir()
            (data_dir / 'news.json').write_text(
                json.dumps(news),
                encoding='utf-8',
            )

            previous_dir = os.getcwd()
            try:
                os.chdir(temp_dir)
                retranslate_missing.retranslate_missing_news()
            finally:
                os.chdir(previous_dir)


if __name__ == '__main__':
    unittest.main()
