"""Unit tests for company identity resolution and website verification."""

import unittest
from signalpost.identity.resolver import assess_website_identity, extract_tokens


class IdentityResolutionTests(unittest.TestCase):
    def test_exact_org_number_on_website_is_verified(self):
        assessment = assess_website_identity(
            company_name="Nordic Energy AS",
            target_org_number="923609016",
            page_data={
                "title": "Nordic Energy AS - Official Website",
                "description": "Leading renewable energy solutions in Norway",
                "text": "Contact us at post@nordicenergy.no. Org nr: 923 609 016. Oslo, Norway.",
            },
        )
        self.assertEqual(assessment["status"], "exact")
        self.assertEqual(assessment["score"], 1.0)
        self.assertTrue(assessment["publishable"])

    def test_conflicting_org_number_is_hard_rejected(self):
        # Page presents a DIFFERENT Norwegian organisation number (987654321 != 923609016)
        assessment = assess_website_identity(
            company_name="Nordic Energy AS",
            target_org_number="923609016",
            page_data={
                "title": "Nordic Energy Solutions",
                "description": "Energy company in Bergen",
                "text": "Operated by Nordic Energy Bergen AS, organisasjonsnummer 987654321.",
            },
        )
        self.assertEqual(assessment["status"], "rejected")
        self.assertEqual(assessment["score"], 0.0)
        self.assertFalse(assessment["publishable"])
        self.assertTrue(any("Conflicting organisation number" in r for r in assessment["reasons"]))

    def test_parked_domain_is_rejected(self):
        assessment = assess_website_identity(
            company_name="Acme Technology AS",
            target_org_number="912345678",
            page_data={
                "title": "Acme Technology - Domain for Sale",
                "description": "Buy this domain at HugeDomains",
                "text": "This domain is for sale. Find the best information on topics related to Acme.",
            },
        )
        self.assertEqual(assessment["status"], "rejected")
        self.assertEqual(assessment["score"], 0.1)
        self.assertFalse(assessment["publishable"])

    def test_exact_multi_token_name_match_is_publishable(self):
        assessment = assess_website_identity(
            company_name="Bergen Maritime Propulsion AS",
            target_org_number="933444555",
            page_data={
                "title": "Bergen Maritime Propulsion",
                "description": "Advanced marine engine systems",
                "text": "Welcome to Bergen Maritime Propulsion. We build cutting-edge propulsion systems for cargo vessels across Scandinavia.",
            },
        )
        self.assertEqual(assessment["status"], "exact")
        self.assertGreaterEqual(assessment["score"], 0.90)
        self.assertTrue(assessment["publishable"])

    def test_unrelated_domain_is_quarantined_not_publishable(self):
        assessment = assess_website_identity(
            company_name="Tromsø Fjord Cruises AS",
            target_org_number="955666777",
            page_data={
                "title": "Global Travel Blog",
                "description": "Backpacking in South America",
                "text": "Today we visited the Andes mountains. Beautiful weather and high altitude.",
            },
        )
        self.assertEqual(assessment["status"], "related_or_uncertain")
        self.assertFalse(assessment["publishable"])

    def test_foreign_namesake_is_quarantined(self):
        assessment = assess_website_identity(
            company_name="Nordic Solutions AS",
            target_org_number="955555555",
            page_data={
                "title": "Nordic Solutions Ltd UK",
                "description": "UK based consulting in London",
                "text": "Registered in England and Wales company no 12345678",
            },
        )
        self.assertEqual(assessment["status"], "related_or_uncertain")
        self.assertFalse(assessment["publishable"])
        self.assertLessEqual(assessment["score"], 0.40)
        self.assertTrue(any("Foreign" in r for r in assessment["reasons"]))

