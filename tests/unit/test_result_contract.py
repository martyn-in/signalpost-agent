"""Unit tests for Builderr OUTPUT_CONTRACT.md envelope format and validation."""

import unittest
from signalpost.result_contract import build_output_envelope, validate_contract_envelope


class ResultContractTests(unittest.TestCase):
    def test_builds_valid_contract_envelope(self):
        sample_profile = {
            "organisation_number": "923609016",
            "name": "Nordic Innovators AS",
            "legal_form": "AS",
            "employees": 15,
            "website": "https://example.no",
            "evidence": {
                "registry": {
                    "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/923609016",
                    "source_class": "official_registry",
                    "retrieved_at": "2026-08-24T06:00:00Z",
                    "content_sha256": "a" * 64,
                    "status": "available",
                },
                "website": {
                    "source_url": "https://example.no",
                    "source_class": "company_owned",
                    "retrieved_at": "2026-08-24T06:00:02Z",
                    "content_sha256": "b" * 64,
                    "status": "available",
                    "value": {"title": "Nordic Innovators"},
                },
            },
        }

        envelope = build_output_envelope(
            profile=sample_profile,
            run_id="run-2026-08-24-a",
            started_at="2026-08-24T06:00:00Z",
            completed_at="2026-08-24T06:00:05Z",
            requests_count=4,
            runtime_ms=5200,
            cost_usd=0.0,
        )

        errors = validate_contract_envelope(envelope)
        self.assertEqual(errors, [], f"Envelope validation errors: {errors}")
        self.assertEqual(envelope["organisation_number"], "923609016")
        self.assertEqual(envelope["run"]["terminal_status"], "completed")
        self.assertGreaterEqual(len(envelope["claims"]), 3)
        self.assertGreaterEqual(len(envelope["evidence"]), 2)

    def test_missing_values_use_valid_availability_states(self):
        # A company without website or accounts
        minimal_profile = {
            "organisation_number": "810059672",
            "name": "AASEN & FARSTAD AS",
            "legal_form": "AS",
            "employees": None,
            "website": None,
            "evidence": {
                "registry": {
                    "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/810059672",
                    "source_class": "official_registry",
                    "retrieved_at": "2026-08-24T06:00:00Z",
                    "content_sha256": "c" * 64,
                }
            },
        }

        envelope = build_output_envelope(
            profile=minimal_profile,
            run_id="run-test",
            started_at="2026-08-24T06:00:00Z",
            completed_at="2026-08-24T06:00:01Z",
        )

        errors = validate_contract_envelope(envelope)
        self.assertEqual(errors, [])

        claims_by_field = {c["field"]: c for c in envelope["claims"]}
        # employees is None -> availability is "not_available", value is None (NOT 0)
        self.assertEqual(claims_by_field["employees"]["availability"], "not_available")
        self.assertIsNone(claims_by_field["employees"]["value"])
        self.assertNotEqual(claims_by_field["employees"]["value"], 0)

        # website is None -> availability is "not_available"
        self.assertEqual(claims_by_field["official_website"]["availability"], "not_available")
        self.assertIsNone(claims_by_field["official_website"]["value"])

        # municipality is None -> availability is "not_available"
        self.assertEqual(claims_by_field["municipality"]["availability"], "not_available")
        self.assertIsNone(claims_by_field["municipality"]["value"])

    def test_missing_company_produces_valid_terminal_envelope(self):
        # When an organisation number is not found in the official registry
        missing_profile = {
            "organisation_number": "999999999",
            "name": None,
            "legal_form": None,
            "employees": None,
            "municipality": None,
            "evidence": {
                "registry": {
                    "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/999999999",
                    "source_class": "official_registry",
                    "retrieved_at": "2026-08-24T06:00:00Z",
                    "content_sha256": "0" * 64,
                    "status": "not_available",
                }
            },
        }

        envelope = build_output_envelope(
            profile=missing_profile,
            run_id="run-missing-test",
            started_at="2026-08-24T06:00:00Z",
            completed_at="2026-08-24T06:00:01Z",
        )

        errors = validate_contract_envelope(envelope)
        self.assertEqual(errors, [])
        self.assertEqual(envelope["organisation_number"], "999999999")
        self.assertEqual(envelope["run"]["terminal_status"], "completed")
        self.assertEqual(len(envelope["claims"]), 6)
        for claim in envelope["claims"]:
            self.assertIn(claim["availability"], ["not_available", "not_applicable"])

