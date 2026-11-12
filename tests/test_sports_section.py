import sys
import unittest
from pathlib import Path

scraper_dir = Path(__file__).resolve().parents[1] / 'scraper'
sys.path.insert(0, str(scraper_dir))

# Restauramos analyze_sentiment si otra prueba lo reemplazó en sys.modules
if 'analyze_sentiment' in sys.modules and not hasattr(sys.modules['analyze_sentiment'], 'analyze_sentiment'):
    del sys.modules['analyze_sentiment']

from multi_scraper import MultiScraper
from group_news import harmonize_group_sections


class SportsSectionDetectionTests(unittest.TestCase):
    def setUp(self):
        self.scraper = MultiScraper()

    def test_baskonia_news_classified_as_deportes(self):
        sec, cat = self.scraper._detect_section(
            title="Baskonia aprovecha su racha europea para enfrentar al Girona",
            url="https://www.gasteizhoy.com/baskonia-girona-acb-jornada-2/",
        )
        self.assertEqual(sec, "deportes")
        self.assertEqual(cat, "Deportes")

    def test_alaves_match_classified_as_deportes(self):
        sec, cat = self.scraper._detect_section(
            title="El Alavés demuestra su potencia goleadora en Azkoitia",
            url="https://www.gasteizhoy.com/anaitasuna-alaves-copa-rey-2026/",
        )
        self.assertEqual(sec, "deportes")
        self.assertEqual(cat, "Deportes")

    def test_alaves_demonym_not_classified_as_deportes(self):
        sec, cat = self.scraper._detect_section(
            title="El 34% de los ingresos de los hogares alaveses se destina al alquiler",
            url="https://www.noticiasdealava.eus/gasteiz/2026/11/11/alquiler.html",
        )
        self.assertNotEqual(sec, "deportes")

        sec2, cat2 = self.scraper._detect_section(
            title="Aenkomer destaca el talento empresarial de Álava",
            url="https://www.noticiasdealava.eus/gasteiz/2026/11/11/aenkomer-reconoce-talento-empresarial-alaves-11745862.html",
        )
        self.assertNotEqual(sec2, "deportes")

    def test_harmonize_group_sections_propagates_deportes(self):
        items = [
            {
                'id': '1',
                'group_id': 'group_test_1',
                'title': 'El Alavés gana el partido',
                'source_section': 'deportes',
                'category': 'Deportes',
            },
            {
                'id': '2',
                'group_id': 'group_test_1',
                'title': 'Victoria albiazul en copa',
                'source_section': None,
                'category': None,
            },
        ]
        harmonize_group_sections(items)
        self.assertEqual(items[1]['source_section'], 'deportes')
        self.assertEqual(items[1]['category'], 'Deportes')


if __name__ == '__main__':
    unittest.main()
