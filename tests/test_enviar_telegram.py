import importlib.util
import unittest
from pathlib import Path


module_path = Path(__file__).resolve().parents[1] / 'scraper' / 'enviar_telegram.py'
module_spec = importlib.util.spec_from_file_location('enviar_telegram', module_path)
enviar_telegram = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(enviar_telegram)


class TelegramNewsTests(unittest.TestCase):
    def test_sorts_null_dates_after_valid_dates(self):
        news = [
            {'id': 'sin-fecha', 'date': None},
            {'id': 'reciente', 'date': '2026-08-03T12:00:00+00:00'},
            {'id': 'antigua', 'date': '2026-08-03T10:00:00+00:00'},
        ]

        news.sort(key=enviar_telegram.get_news_sort_key)

        self.assertEqual(
            [item['id'] for item in news],
            ['antigua', 'reciente', 'sin-fecha'],
        )


if __name__ == '__main__':
    unittest.main()
