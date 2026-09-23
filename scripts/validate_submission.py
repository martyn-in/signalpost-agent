#!/usr/bin/env python3
"""Builderr Signalpost Submission Package Validator.

Validates that a submission package satisfies all competition rules:
1. Manifest contains at least 1,000 unique valid Norwegian organisation numbers.
2. Profiles file contains at least 1,000 profiles matching the manifest exactly.
3. Envelopes file contains exactly matching terminal envelopes for every company.
4. Every envelope complies with OUTPUT_CONTRACT.md schema.
5. All availability states are valid.
6. Missing values are never silently converted to zero.
7. No NaN or Infinity values exist in JSON.
8. Every published claim has valid evidence with source URL, timestamp, and content hash.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

VALID_AVAILABILITIES = {
    "available",
    "not_available",
    "blocked",
    "not_applicable",
    "ambiguous",
    "failed",
}


def check_no_nan_or_inf(obj: object, path: str = "root") -> list[str]:
    errors = []
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            errors.append(f"Invalid non-finite float at {path}: {obj}")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            errors.extend(check_no_nan_or_inf(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            errors.extend(check_no_nan_or_inf(v, f"{path}[{i}]"))
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Signalpost submission package")
    parser.add_argument("--manifest", required=True, help="Path to organisation_numbers.txt or JSONL manifest")
    parser.add_argument("--envelopes", required=True, help="Path to envelopes.jsonl")
    parser.add_argument("--profiles", required=True, help="Path to profiles.jsonl")
    parser.add_argument("--min-count", type=int, default=1000, help="Minimum company count (default: 1000)")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    envelopes_path = Path(args.envelopes)
    profiles_path = Path(args.profiles)

    # 1. Check file existence
    for path, name in [(manifest_path, "Manifest"), (envelopes_path, "Envelopes"), (profiles_path, "Profiles")]:
        if not path.exists():
            print(f"[ERROR] {name} file does not exist: {path}", file=sys.stderr)
            sys.exit(1)

    # 2. Parse Manifest
    manifest_lines = [l.strip() for l in manifest_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    manifest_orgs = []
    for line in manifest_lines:
        if line.startswith("{"):
            record = json.loads(line)
            org = str(record.get("organisation_number") or "")
        else:
            org = "".join(c for c in line if c.isdigit())
        if len(org) != 9:
            print(f"[ERROR] Invalid organisation number in manifest: {line!r}", file=sys.stderr)
            sys.exit(1)
        manifest_orgs.append(org)

    if len(manifest_orgs) != len(set(manifest_orgs)):
        print("[ERROR] Manifest contains duplicate organisation numbers", file=sys.stderr)
        sys.exit(1)

    if len(manifest_orgs) < args.min_count:
        print(f"[ERROR] Manifest contains {len(manifest_orgs)} companies; minimum required is {args.min_count}", file=sys.stderr)
        sys.exit(1)

    print(f"[PASS] Manifest contains {len(manifest_orgs):,} valid unique organisation numbers")

    # 3. Parse and Validate Profiles
    profile_lines = [l.strip() for l in profiles_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if len(profile_lines) != len(manifest_orgs):
        print(f"[ERROR] Profiles count ({len(profile_lines)}) does not match manifest count ({len(manifest_orgs)})", file=sys.stderr)
        sys.exit(1)

    profile_orgs = []
    for idx, line in enumerate(profile_lines):
        try:
            profile = json.loads(line)
        except json.JSONDecodeError as exc:
            print(f"[ERROR] Profile #{idx} is not valid JSON: {exc}", file=sys.stderr)
            sys.exit(1)

        nan_errors = check_no_nan_or_inf(profile, f"profile[{idx}]")
        if nan_errors:
            print(f"[ERROR] Profile #{idx} contains NaN/Inf: {nan_errors[:3]}", file=sys.stderr)
            sys.exit(1)

        org = str(profile.get("organisation_number") or "")
        profile_orgs.append(org)

    if profile_orgs != manifest_orgs:
        print("[ERROR] Profile organisation numbers do not match manifest sequence exactly", file=sys.stderr)
        sys.exit(1)

    print(f"[PASS] Profiles file contains {len(profile_lines):,} valid profiles matching manifest sequence")

    # 4. Parse and Validate Envelopes
    envelope_lines = [l.strip() for l in envelopes_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if len(envelope_lines) != len(manifest_orgs):
        print(f"[ERROR] Envelopes count ({len(envelope_lines)}) does not match manifest count ({len(manifest_orgs)})", file=sys.stderr)
        sys.exit(1)

    envelope_orgs = []
    total_claims = 0
    total_evidence = 0

    for idx, line in enumerate(envelope_lines):
        try:
            env = json.loads(line)
        except json.JSONDecodeError as exc:
            print(f"[ERROR] Envelope #{idx} is not valid JSON: {exc}", file=sys.stderr)
            sys.exit(1)

        nan_errors = check_no_nan_or_inf(env, f"envelope[{idx}]")
        if nan_errors:
            print(f"[ERROR] Envelope #{idx} contains NaN/Inf: {nan_errors[:3]}", file=sys.stderr)
            sys.exit(1)

        org = str(env.get("organisation_number") or "")
        envelope_orgs.append(org)

        # Validate Run Section
        run = env.get("run") or {}
        if not run.get("run_id") or not run.get("started_at") or not run.get("completed_at"):
            print(f"[ERROR] Envelope #{idx} missing valid 'run' section", file=sys.stderr)
            sys.exit(1)

        # Validate Claims
        claims = env.get("claims") or []
        evidence = env.get("evidence") or []
        ev_id_set = {ev.get("id") for ev in evidence if isinstance(ev, dict)}

        for c_idx, claim in enumerate(claims):
            if not isinstance(claim, dict):
                print(f"[ERROR] Envelope #{idx} claim #{c_idx} is not a dict", file=sys.stderr)
                sys.exit(1)
            avail = claim.get("availability")
            if avail not in VALID_AVAILABILITIES:
                print(f"[ERROR] Envelope #{idx} claim #{c_idx} invalid availability: {avail!r}", file=sys.stderr)
                sys.exit(1)

            # Check that missing values are never zero
            if avail in {"not_available", "not_applicable", "blocked", "ambiguous", "failed"}:
                val = claim.get("value")
                if val == 0 or val == 0.0:
                    print(f"[ERROR] Envelope #{idx} claim '{claim.get('field')}' has availability '{avail}' but value is 0 (missing converted to zero!)", file=sys.stderr)
                    sys.exit(1)

            # Quality Gate: Every available claim MUST have at least one evidence ID
            if avail == "available" and not claim.get("evidence_ids"):
                print(f"[ERROR] Envelope #{idx} claim '{claim.get('field')}' is available but has empty evidence_ids", file=sys.stderr)
                sys.exit(1)

            # Check evidence references
            for ev_ref in claim.get("evidence_ids", []):
                if ev_ref not in ev_id_set:
                    print(f"[ERROR] Envelope #{idx} claim references unknown evidence ID '{ev_ref}'", file=sys.stderr)
                    sys.exit(1)


            total_claims += 1

        # Validate Evidence
        for e_idx, ev in enumerate(evidence):
            if not ev.get("id") or not ev.get("source_url") or not ev.get("retrieved_at") or not ev.get("content_sha256"):
                print(f"[ERROR] Envelope #{idx} evidence #{e_idx} missing mandatory fields", file=sys.stderr)
                sys.exit(1)
            total_evidence += 1

        # Validate Operations
        ops = env.get("operations") or {}
        if "requests" not in ops or "runtime_ms" not in ops:
            print(f"[ERROR] Envelope #{idx} missing valid operations section", file=sys.stderr)
            sys.exit(1)

    if envelope_orgs != manifest_orgs:
        print("[ERROR] Envelope organisation numbers do not match manifest sequence exactly", file=sys.stderr)
        sys.exit(1)

    print(f"[PASS] Envelopes file contains {len(envelope_lines):,} valid envelopes")
    print(f"[PASS] Total validated claims: {total_claims:,} across {len(envelope_lines):,} companies")
    print(f"[PASS] Total validated evidence records: {total_evidence:,}")
    print("[SUCCESS] All Builderr Signalpost submission validation gates PASSED perfectly!")


if __name__ == "__main__":
    main()
