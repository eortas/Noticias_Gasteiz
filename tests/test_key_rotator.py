import time
import unittest
from scraper.key_rotator import get_next_key, report_key_rate_limited, is_key_cooling
from scraper.analyze_sentiment import translate_article_to_languages

class TestKeyRotator(unittest.TestCase):
    def test_round_robin_rotation(self):
        keys = ["k1", "k2", "k3"]
        pool = f"test_pool_{time.time()}"
        
        # Comprobamos que rota en orden
        selected1 = get_next_key(keys, pool)
        selected2 = get_next_key(keys, pool)
        selected3 = get_next_key(keys, pool)
        selected4 = get_next_key(keys, pool)
        
        self.assertEqual(selected1, "k1")
        self.assertEqual(selected2, "k2")
        self.assertEqual(selected3, "k3")
        self.assertEqual(selected4, "k1")

    def test_cooldown_avoids_rate_limited_keys(self):
        keys = ["key_a", "key_b", "key_c"]
        pool = f"test_cooldown_{time.time()}"
        
        # Marcamos key_a con rate limit
        report_key_rate_limited("key_a", cooldown_seconds=10)
        self.assertTrue(is_key_cooling("key_a"))
        
        # Al pedir claves, solo debe devolver key_b y key_c
        picked = [get_next_key(keys, pool) for _ in range(4)]
        self.assertNotIn("key_a", picked)
        self.assertTrue(all(k in ["key_b", "key_c"] for k in picked))

    def test_empty_keys_returns_none(self):
        self.assertIsNone(get_next_key([], "test_empty"))
        self.assertIsNone(get_next_key([None, ""], "test_empty"))

    def test_translate_article_to_languages_handles_empty(self):
        res = translate_article_to_languages("Título", "Cuerpo", target_langs=[])
        self.assertEqual(res, {})

if __name__ == '__main__':
    unittest.main()
