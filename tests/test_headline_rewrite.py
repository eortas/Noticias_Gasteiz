import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


scraper_dir = Path(__file__).resolve().parents[1] / 'scraper'
sys.path.insert(0, str(scraper_dir))

import analyze_sentiment
from analyze_sentiment import is_headline_rewritten


class HeadlineRewriteTests(unittest.TestCase):
    def test_rejects_identical_headline(self):
        title = 'La AP-68 tendrá un peaje provisional en Zambrana'

        self.assertFalse(is_headline_rewritten(title, title))

    def test_rejects_only_case_and_punctuation_changes(self):
        original = 'La AP-68 tendrá un peaje provisional en Zambrana'
        candidate = 'LA AP-68 TENDRÁ UN PEAJE PROVISIONAL EN ZAMBRANA.'

        self.assertFalse(is_headline_rewritten(original, candidate))

    def test_accepts_a_faithful_new_construction(self):
        original = 'La AP-68 tendrá un peaje provisional en Zambrana'
        candidate = 'Zambrana contará con un peaje provisional en la AP-68'

        self.assertTrue(is_headline_rewritten(original, candidate))

    def test_rewriter_retries_when_model_copies_original(self):
        original = 'La AP-68 tendrá un peaje provisional en Zambrana'
        rewritten = 'Zambrana contará con un peaje provisional en la AP-68'
        responses = iter([original, rewritten])

        class FakeCompletions:
            def create(self, **kwargs):
                message = SimpleNamespace(content=next(responses))
                return SimpleNamespace(choices=[SimpleNamespace(message=message)])

        class FakeGroq:
            def __init__(self, api_key):
                self.chat = SimpleNamespace(completions=FakeCompletions())

        with patch.dict(os.environ, {'GROQ_REWRITE_2': 'test-key'}):
            with patch.object(analyze_sentiment, 'Groq', FakeGroq):
                with patch.object(analyze_sentiment, 'get_next_key', return_value='test-key'):
                    result = analyze_sentiment._rewrite_chunk(original, 'TÍTULO')

        self.assertEqual(result, rewritten)

    def test_mistral_retries_when_final_title_copies_original(self):
        original = 'La AP-68 tendrá un peaje provisional en Zambrana'
        rewritten = 'Zambrana contará con un peaje provisional en la AP-68'
        responses = iter([original, rewritten])

        class FakeChat:
            def complete(self, **kwargs):
                final_title = next(responses)
                content = json.dumps({
                    'is_faithful': True,
                    'is_rewritten': final_title != original,
                    'final_title': final_title,
                })
                message = SimpleNamespace(content=content)
                return SimpleNamespace(choices=[SimpleNamespace(message=message)])

        class FakeMistral:
            def __init__(self, api_key):
                self.chat = FakeChat()

        with patch.object(analyze_sentiment, 'get_mistral_keys', return_value=['test-key']):
            with patch.object(analyze_sentiment, 'get_next_key', return_value='test-key'):
                with patch.object(analyze_sentiment, 'Mistral', FakeMistral):
                    result = analyze_sentiment.verify_headline_with_mistral(
                        original,
                        original,
                    )

        self.assertEqual(result, rewritten)


if __name__ == '__main__':
    unittest.main()
