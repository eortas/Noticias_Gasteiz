import json
import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


scraper_dir = Path(__file__).resolve().parents[1] / 'scraper'
sys.path.insert(0, str(scraper_dir))


if 'groq' not in sys.modules:
    groq_module = types.ModuleType('groq')
    groq_module.Groq = object
    sys.modules['groq'] = groq_module

if 'mistralai.client.sdk' not in sys.modules:
    mistral_module = types.ModuleType('mistralai')
    mistral_client_module = types.ModuleType('mistralai.client')
    mistral_sdk_module = types.ModuleType('mistralai.client.sdk')
    mistral_sdk_module.Mistral = object
    sys.modules['mistralai'] = mistral_module
    sys.modules['mistralai.client'] = mistral_client_module
    sys.modules['mistralai.client.sdk'] = mistral_sdk_module

if 'dotenv' not in sys.modules:
    dotenv_module = types.ModuleType('dotenv')
    dotenv_module.load_dotenv = lambda: None
    sys.modules['dotenv'] = dotenv_module

module_path = scraper_dir / 'analyze_sentiment.py'
module_spec = importlib.util.spec_from_file_location('sentiment_under_test', module_path)
analyze_sentiment = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(analyze_sentiment)


class SentimentTests(unittest.TestCase):
    def test_always_uses_llm_instead_of_keyword_heuristics(self):
        captured = {}

        class FakeChat:
            def complete(self, **kwargs):
                captured['prompt'] = kwargs['messages'][0]['content']
                result = {
                    'sentiment': 'neutral',
                    'score': 0,
                    'category': 'Cultura',
                }
                message = SimpleNamespace(content=json.dumps(result))
                return SimpleNamespace(choices=[SimpleNamespace(message=message)])

        class FakeMistral:
            def __init__(self, api_key):
                self.chat = FakeChat()

        text = 'Gran fiesta con premios, pero también problemas y protestas'
        with patch.dict(os.environ, {'MISTRAL_VALORACION': 'test-key'}, clear=True):
            with patch.object(analyze_sentiment, 'Mistral', FakeMistral):
                with patch.object(analyze_sentiment, 'get_mistral_sentiment_keys', return_value=['test-key']):
                    with patch.object(analyze_sentiment, 'get_next_key', return_value='test-key'):
                        result = analyze_sentiment.analyze_sentiment(text)

        self.assertEqual(result, ('neutral', 0.0, 'Cultura'))
        self.assertIn('fiestas patronales', captured['prompt'])
        self.assertIn('actos sociales', captured['prompt'])
        self.assertIn('clero, curas, obispos', captured['prompt'])

    def test_missing_llm_key_returns_neutral(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(analyze_sentiment, 'get_mistral_sentiment_keys', return_value=[]):
                result = analyze_sentiment.analyze_sentiment('Robo con una persona herida')

        self.assertEqual(result, ('neutral', 0.0, 'Sociedad'))

    def test_normalizes_inconsistent_llm_score(self):
        result = analyze_sentiment.normalize_sentiment_result({
            'sentiment': 'negativa',
            'score': 0.7,
            'category': 'Sucesos',
        })

        self.assertEqual(result, ('negativa', -0.7, 'Sucesos'))

    def test_uses_both_dedicated_mistral_keys(self):
        env = {
            'MISTRAL_VALORACION': 'first-key',
            'MISTRAL_VALORACION2': 'second-key',
        }
        with patch.dict(os.environ, env, clear=True):
            keys = analyze_sentiment.get_mistral_sentiment_keys()

        self.assertEqual(keys, ['first-key', 'second-key'])


if __name__ == '__main__':
    unittest.main()
