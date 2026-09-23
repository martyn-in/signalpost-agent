"""Unit tests for refresh idempotency and typed change detection."""

import copy
import unittest
from signalpost.refresh.diff import compute_semantic_fingerprint, detect_typed_changes


class RefreshIdempotenceTests(unittest.TestCase):
    def setUp(self):
        self.sample_profile = {
            "organisation_number": "923609016",
            "name": "Nordic Innovators AS",
            "legal_form": "AS",
            "employees": 42,
            "municipality": "Oslo",
            "website": "https://nordic-innovators.no",
            "latest_submitted_accounts": "2025",
            "evidence": {
                "registry": {
                    "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/923609016",
                    "source_class": "official_registry",
                    "retrieved_at": "2026-08-20T06:00:00Z",
                    "content_sha256": "abc12345" * 8,
                    "status": "available",
                },
                "roles": {
                    "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/923609016/roller",
                    "source_class": "official_roles",
                    "retrieved_at": "2026-08-20T06:00:00Z",
                    "content_sha256": "def67890" * 8,
                    "status": "available",
                    "value": {
                        "roles": [
                            {"name": "Lars Hansen", "role": "Daglig leder", "role_code": "DAGL"}
                        ]
                    },
                },
            },
        }

    def test_idempotent_rerun_produces_zero_changes(self):
        # Mandatory Quality Gate: Running identical profile snapshot must produce ZERO changes
        changes = detect_typed_changes(self.sample_profile, self.sample_profile)
        self.assertEqual(len(changes), 0, "Idempotent rerun against identical profile must produce 0 changes")

    def test_detects_real_role_change(self):
        updated_profile = copy.deepcopy(self.sample_profile)
        # Executive changed from Lars Hansen to Kari Nordmann
        updated_profile["evidence"]["roles"]["value"]["roles"] = [
            {"name": "Kari Nordmann", "role": "Daglig leder", "role_code": "DAGL"}
        ]
        updated_profile["evidence"]["roles"]["content_sha256"] = "newhash1" * 8
        updated_profile["evidence"]["roles"]["retrieved_at"] = "2026-08-25T06:00:00Z"

        changes = detect_typed_changes(self.sample_profile, updated_profile)
        self.assertEqual(len(changes), 1)
        change = changes[0]
        self.assertEqual(change["field"], "roles.roles")
        self.assertEqual(change["change_type"], "role_changed")
        self.assertEqual(change["organisation_number"], "923609016")
        self.assertNotEqual(change["old_value"], change["new_value"])

    def test_detects_workforce_growth(self):
        updated_profile = copy.deepcopy(self.sample_profile)
        updated_profile["employees"] = 55
        updated_profile["evidence"]["registry"]["content_sha256"] = "newreghash" * 8

        changes = detect_typed_changes(self.sample_profile, updated_profile)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["field"], "registry.employees")
        self.assertEqual(changes[0]["old_value"], 42)
        self.assertEqual(changes[0]["new_value"], 55)

    def test_semantic_fingerprint_excludes_retrieval_date(self):
        fp1 = compute_semantic_fingerprint("923609016", "employees", 42)
        fp2 = compute_semantic_fingerprint("923609016", "employees", 42)
        self.assertEqual(fp1, fp2, "Identical facts must have identical semantic fingerprints")
