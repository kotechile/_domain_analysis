import os
import sys
import unittest

sys.path.append(os.path.join(os.getcwd(), 'backend', 'src'))

from services.csv_parser_service import CSVParserService


class TestCSVParserService(unittest.TestCase):
    def setUp(self):
        self.parser = CSVParserService()

    def test_parse_single_domain_scores_whitelisted_tld(self):
        parsed = self.parser.parse_single_domain('brandable.com')

        self.assertTrue(parsed.eligible_for_scoring)
        self.assertIsNone(parsed.filter_reason)
        self.assertIsNotNone(parsed.total_meaning_score)
        self.assertGreater(parsed.total_meaning_score, 0)

    def test_parse_single_domain_rejects_non_whitelisted_tld(self):
        parsed = self.parser.parse_single_domain('brandable.xyz')

        self.assertFalse(parsed.eligible_for_scoring)
        self.assertEqual(parsed.total_meaning_score, None)
        self.assertIn('.xyz', parsed.filter_reason)


if __name__ == '__main__':
    unittest.main()
