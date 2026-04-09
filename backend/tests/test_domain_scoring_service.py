import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.append(os.path.join(os.getcwd(), "backend", "src"))

from models.domain_analysis import NamecheapDomain
from services.domain_scoring_service import DomainScoringService


class TestDomainScoringService(unittest.TestCase):
    def setUp(self):
        self.service = DomainScoringService()

    def test_rejects_non_whitelist_tld(self):
        scored = self.service.score_domain(NamecheapDomain(name="brandable.xyz"))

        self.assertEqual(scored.filter_status, "FAIL")
        self.assertIn(".xyz", scored.filter_reason)
        self.assertIsNone(scored.total_meaning_score)

    def test_scores_clean_business_compound_higher_than_numeric_noise(self):
        strong = self.service.score_domain(NamecheapDomain(name="brightpath.com"))
        weak = self.service.score_domain(NamecheapDomain(name="025ebi.com"))

        self.assertEqual(strong.filter_status, "PASS")
        self.assertEqual(weak.filter_status, "FAIL")
        self.assertGreater(strong.total_meaning_score, 0)

    def test_ai_tld_is_more_valuable_for_ai_native_terms(self):
        ai_native = self.service.score_domain(NamecheapDomain(name="agentforge.ai"))
        generic = self.service.score_domain(NamecheapDomain(name="orchard.ai"))

        self.assertEqual(ai_native.filter_status, "PASS")
        self.assertEqual(generic.filter_status, "PASS")
        self.assertGreater(ai_native.tld_score, generic.tld_score)

    def test_age_is_only_a_modest_bonus_in_v2(self):
        fresh = self.service.score_domain(NamecheapDomain(name="brightpath.com"))
        aged = self.service.score_domain(
            NamecheapDomain(
                name="brightpath.com",
                registered_date=datetime(2008, 1, 1, tzinfo=timezone.utc),
            )
        )

        self.assertEqual(fresh.filter_status, "PASS")
        self.assertEqual(aged.filter_status, "PASS")
        self.assertGreater(aged.total_meaning_score, fresh.total_meaning_score)
        self.assertLess(aged.total_meaning_score - fresh.total_meaning_score, 12.0)


if __name__ == "__main__":
    unittest.main()
