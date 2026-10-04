"""Zero-score regression test for Builderr official evaluation.

Guarantees that:
1. An arbitrary company batch (including unseen companies outside any snapshot)
   runs through the official batch execution entrypoint.
2. The agent produces evaluator-visible accepted claims with full evidence.
3. Source URLs and timestamps are serialized and non-empty.
4. Terminal status is 'completed'.
5. The exact technical bug that resulted in official Recall=0 and Evidence=0
   can never recur.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signalpost.result_contract import validate_contract_envelope


def test_zero_score_regression_on_arbitrary_unseen_companies() -> None:
    # 916627939: - P A L M E R A - (Confirmed not present in local snapshot)
    # 810034882: SANDNES ELEKTRISKE AS (Known operating company)
    test_orgs = ["916627939", "810034882"]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        input_file = tmp_path / "test_companies.txt"
        input_file.write_text("\n".join(test_orgs) + "\n", encoding="utf-8")

        output_file = tmp_path / "envelopes.jsonl"
        report_file = tmp_path / "report.json"

        # Run the official command with ONLY the 3 arguments Builderr provides
        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "run_competition_batch.py"),
            "--organisations",
            str(input_file),
            "--output",
            str(output_file),
            "--report",
            str(report_file),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
        assert result.returncode == 0, f"Run failed with code {result.returncode}:\n{result.stderr}"

        assert output_file.exists(), "Output envelopes file was not created"
        assert report_file.exists(), "Summary report file was not created"

        lines = [line.strip() for line in output_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(lines) == len(test_orgs), f"Expected {len(test_orgs)} envelopes, got {len(lines)}"

        envelopes = [json.loads(line) for line in lines]
        for env in envelopes:
            org = env["organisation_number"]
            assert org in test_orgs, f"Unexpected organisation number {org}"

            # Contract validation
            errs = validate_contract_envelope(env)
            assert not errs, f"Validation errors for {org}: {errs}"

            # Terminal status must be completed
            assert env["run"]["terminal_status"] == "completed"

            # CRITICAL ZERO-SCORE GUARDS:
            # 1. Must have accepted claims
            claims = env.get("claims", [])
            assert len(claims) > 0, f"No claims found for {org}"

            available_claims = [c for c in claims if c.get("availability") == "available"]
            assert len(available_claims) >= 3, f"Expected at least 3 available claims for {org}, got {len(available_claims)}"

            # 2. Must have evidence items
            evidence_items = env.get("evidence", [])
            assert len(evidence_items) >= 1, f"Expected at least 1 evidence item for {org}, got {len(evidence_items)}"

            ev_id_map = {e["id"]: e for e in evidence_items}

            # 3. Every available claim MUST link to valid evidence
            for c in available_claims:
                e_refs = c.get("evidence_ids", [])
                assert len(e_refs) >= 1, f"Available claim '{c.get('field')}' has no evidence_ids"
                for ref in e_refs:
                    assert ref in ev_id_map, f"Evidence ID '{ref}' not found in evidence items"
                    ev = ev_id_map[ref]
                    assert ev.get("source_url"), f"Evidence '{ref}' has empty source_url"
                    assert ev.get("source_url", "").startswith(("http://", "https://")), f"Invalid source_url: {ev.get('source_url')}"
                    assert ev.get("retrieved_at"), f"Evidence '{ref}' has empty retrieved_at"
                    assert "T" in ev.get("retrieved_at", ""), f"retrieved_at not ISO-8601: {ev.get('retrieved_at')}"

            # 4. Specific assertions for unseen company 916627939
            if org == "916627939":
                claim_by_field = {c["field"]: c for c in claims}
                assert claim_by_field["legal_name"]["availability"] == "available"
                assert claim_by_field["legal_name"]["value"] == "- P A L M E R A -"
                assert claim_by_field["legal_form"]["availability"] == "available"
                assert claim_by_field["legal_form"]["value"] == "FLI"
                assert claim_by_field["municipality"]["availability"] == "available"
                assert claim_by_field["municipality"]["value"] == "BERGEN"
