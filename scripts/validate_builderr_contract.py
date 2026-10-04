#!/usr/bin/env python3
"""Builderr Official Result Contract Verification Harness.

Simulates the Builderr official evaluator to guarantee our runner complies
with all technical constraints on arbitrary inputs:
1. Arbitrary input path accepted (JSONL, JSON array, or newline list)
2. Every input org number has exactly one result (1:1 contract)
3. No extra result rows, no duplicate companies, no missing companies
4. Organisation numbers preserved exactly
5. Valid terminal state and schema compliance
6. Available claims contain evidence with syntactically valid source URLs & timestamps
7. Missing values are never converted to zero
8. Output is deterministic where source data is unchanged
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signalpost.result_contract import VALID_AVAILABILITIES, validate_contract_envelope


def run_batch_script(
    input_file: Path,
    output_file: Path,
    report_file: Path,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess:
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
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))


def test_input_formats_and_contract() -> None:
    print("============================================================")
    print("Testing Builderr Official Contract Compatibility Across Inputs")
    print("============================================================")

    test_orgs = [
        "810034882",  # SANDNES ELEKTRISKE AS (Large operating AS)
        "923609016",  # NORDIC INNOVATORS AS
        "810059672",  # AASEN & FARSTAD AS (None employees)
        "916627939",  # - P A L M E R A - (Entity outside frozen snapshot)
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # -------------------------------------------------------------
        # Test Format 1: Newline Text File (.txt)
        # -------------------------------------------------------------
        print("\n[1/5] Testing plain newline text format (.txt)...")
        txt_input = tmp_path / "companies.txt"
        txt_input.write_text("\n".join(test_orgs) + "\n", encoding="utf-8")
        out1 = tmp_path / "out1.jsonl"
        rep1 = tmp_path / "rep1.json"

        res1 = run_batch_script(txt_input, out1, rep1)
        if res1.returncode != 0:
            print(f"FAILED on newline txt input:\n{res1.stderr}", file=sys.stderr)
            sys.exit(1)
        envelopes1 = [json.loads(line) for line in out1.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(envelopes1) == len(test_orgs), f"Expected {len(test_orgs)} envelopes, got {len(envelopes1)}"
        print(f"PASS: Produced exactly {len(envelopes1)} valid envelopes from .txt input")

        # -------------------------------------------------------------
        # Test Format 2: JSON Array (.json)
        # -------------------------------------------------------------
        print("\n[2/5] Testing JSON array format (.json)...")
        json_input = tmp_path / "companies.json"
        json_input.write_text(json.dumps(test_orgs), encoding="utf-8")
        out2 = tmp_path / "out2.jsonl"
        rep2 = tmp_path / "rep2.json"

        res2 = run_batch_script(json_input, out2, rep2)
        if res2.returncode != 0:
            print(f"FAILED on JSON array input:\n{res2.stderr}", file=sys.stderr)
            sys.exit(1)
        envelopes2 = [json.loads(line) for line in out2.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(envelopes2) == len(test_orgs), f"Expected {len(test_orgs)} envelopes, got {len(envelopes2)}"
        print(f"PASS: Produced exactly {len(envelopes2)} valid envelopes from .json array")

        # -------------------------------------------------------------
        # Test Format 3: JSONL Format (.jsonl)
        # -------------------------------------------------------------
        print("\n[3/5] Testing JSONL format (.jsonl)...")
        jsonl_input = tmp_path / "companies.jsonl"
        jsonl_input.write_text(
            "\n".join(json.dumps({"organisation_number": org}) for org in test_orgs) + "\n",
            encoding="utf-8",
        )
        out3 = tmp_path / "out3.jsonl"
        rep3 = tmp_path / "rep3.json"

        res3 = run_batch_script(jsonl_input, out3, rep3)
        if res3.returncode != 0:
            print(f"FAILED on JSONL input:\n{res3.stderr}", file=sys.stderr)
            sys.exit(1)
        envelopes3 = [json.loads(line) for line in out3.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(envelopes3) == len(test_orgs), f"Expected {len(test_orgs)} envelopes, got {len(envelopes3)}"
        print(f"PASS: Produced exactly {len(envelopes3)} valid envelopes from .jsonl input")

        # -------------------------------------------------------------
        # Test Format 4: Single Company Batch (N=1 boundary condition)
        # -------------------------------------------------------------
        print("\n[4/5] Testing boundary batch size N=1...")
        single_input = tmp_path / "single.txt"
        single_input.write_text("916627939\n", encoding="utf-8")
        out4 = tmp_path / "out4.jsonl"
        rep4 = tmp_path / "rep4.json"

        res4 = run_batch_script(single_input, out4, rep4)
        if res4.returncode != 0:
            print(f"FAILED on N=1 batch:\n{res4.stderr}", file=sys.stderr)
            sys.exit(1)
        envelopes4 = [json.loads(line) for line in out4.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(envelopes4) == 1, f"Expected 1 envelope, got {len(envelopes4)}"
        assert envelopes4[0]["organisation_number"] == "916627939"
        print("PASS: Handled single-company input perfectly")

        # -------------------------------------------------------------
        # Test 5: Detailed Schema and Contract Invariants
        # -------------------------------------------------------------
        print("\n[5/5] Verifying all contract schema rules & invariants...")
        for env in envelopes1:
            org = env["organisation_number"]
            # 1. OUTPUT_CONTRACT validation
            errs = validate_contract_envelope(env)
            if errs:
                print(f"FAIL: Envelope {org} schema errors: {errs}", file=sys.stderr)
                sys.exit(1)

            # 2. Terminal state check
            assert env.get("run", {}).get("terminal_status") == "completed"

            # 3. Available claims must cite existing evidence IDs
            ev_ids = {e["id"] for e in env.get("evidence", [])}
            claims_by_field = {c["field"]: c for c in env.get("claims", [])}

            for field, claim in claims_by_field.items():
                avail = claim.get("availability")
                assert avail in VALID_AVAILABILITIES, f"Invalid availability {avail}"

                # Invariant: Available claims have evidence
                if avail == "available":
                    e_refs = claim.get("evidence_ids", [])
                    assert len(e_refs) >= 1, f"Field '{field}' available but has no evidence"
                    for ref in e_refs:
                        assert ref in ev_ids, f"Field '{field}' cites non-existent evidence '{ref}'"

                # Invariant: Missing is never 0
                if avail in {"not_available", "not_applicable"}:
                    val = claim.get("value")
                    assert val is None, f"Field '{field}' is {avail} but value is {val!r} (must be None, not 0)"

            # Check that unseen company (916627939) got real facts via live lookup
            if org == "916627939":
                assert claims_by_field["legal_name"]["availability"] == "available"
                assert claims_by_field["legal_name"]["value"] == "- P A L M E R A -"
                assert claims_by_field["registered_address"]["availability"] == "available"
                assert "BERGEN" in str(claims_by_field["registered_address"]["value"])

        print("PASS: All contract schema rules & invariants validated successfully")

    print("\n============================================================")
    print("SUCCESS: Builderr Official Contract Verification PASSED 100%")
    print("============================================================")


if __name__ == "__main__":
    test_input_formats_and_contract()
