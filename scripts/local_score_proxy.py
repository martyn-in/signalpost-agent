#!/usr/bin/env python3
"""Local Engineering Score Proxy for Signalpost development and trend tracking.

============================================================
LOCAL ENGINEERING PROXY — NOT BUILDERR OFFICIAL SCORE
============================================================
The evaluator's ground-truth reference collection is held privately by Builderr.
This local engineering proxy estimates component performance according to official
public criteria:
- Recall & Coverage (50 points): 70% company breadth + 30% individual fact coverage
- Precision & Evidence (30 points): Invariant that 100% of available claims have valid,
  syntactically verified, non-empty evidence without known false-attributions
- Synthesis (12 points): High-density grounded summary mapping 100% of statements
  to verified claims
- UX & Inspection (8 points): Machine-parsable contract compliance, interactive viewing,
  and auditability
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signalpost.result_contract import validate_contract_envelope


def compute_local_proxy_score(envelopes_path: Path) -> dict[str, Any]:
    lines = [line.strip() for line in envelopes_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    envelopes = [json.loads(line) for line in lines]
    total_companies = len(envelopes)

    if total_companies == 0:
        return {"total_score": 0.0, "components": {}}

    # -------------------------------------------------------------
    # 1. Recall & Coverage Proxy (Max 50 points)
    # 70% Company Breadth (>=1 verified fact) = 35 pts
    # 30% Fact Depth (available facts across core categories) = 15 pts
    # -------------------------------------------------------------
    companies_with_facts = 0
    total_available_claims = 0
    total_possible_core_claims = total_companies * 10  # 10 core fields

    for env in envelopes:
        claims = env.get("claims", [])
        avail_count = sum(1 for c in claims if c.get("availability") == "available")
        if avail_count >= 1:
            companies_with_facts += 1
        total_available_claims += avail_count

    company_breadth_ratio = companies_with_facts / total_companies
    breadth_score = company_breadth_ratio * 35.0

    # Fact depth ratio (capped at 1.0)
    depth_ratio = min(1.0, total_available_claims / total_possible_core_claims)
    depth_score = depth_ratio * 15.0

    recall_proxy = breadth_score + depth_score

    # -------------------------------------------------------------
    # 2. Precision & Evidence Proxy (Max 30 points)
    # Invariant: Every available claim MUST have >=1 valid evidence item
    # Deductions for contract schema errors or unbacked available claims
    # -------------------------------------------------------------
    contract_violations = 0
    unsupported_claims = 0
    evidence_backed_claims = 0

    for env in envelopes:
        errs = validate_contract_envelope(env)
        if errs:
            contract_violations += len(errs)

        ev_ids = {e.get("id") for e in env.get("evidence", [])}
        for c in env.get("claims", []):
            if c.get("availability") == "available":
                e_refs = c.get("evidence_ids", [])
                if not e_refs or not all(ref in ev_ids for ref in e_refs):
                    unsupported_claims += 1
                else:
                    evidence_backed_claims += 1

    total_evaluated_available = evidence_backed_claims + unsupported_claims
    grounded_ratio = (evidence_backed_claims / total_evaluated_available) if total_evaluated_available > 0 else 1.0

    # Hard deduction for contract violations or unsupported claims
    precision_deductions = (unsupported_claims * 2.0) + (contract_violations * 5.0)
    evidence_proxy = max(0.0, (grounded_ratio * 30.0) - precision_deductions)

    # -------------------------------------------------------------
    # 3. Synthesis Proxy (Max 12 points)
    # Grounded corporate summary answering core questions
    # -------------------------------------------------------------
    valid_summaries = 0
    for env in envelopes:
        summary_text = env.get("summary", {}).get("text", "")
        # Non-empty and substantive
        if len(summary_text.strip()) >= 40:
            valid_summaries += 1

    synthesis_ratio = valid_summaries / total_companies
    synthesis_proxy = synthesis_ratio * 12.0

    # -------------------------------------------------------------
    # 4. UX Proxy (Max 8 points)
    # Terminal envelope valid, machine-parsable, unique org keys, 1:1 match
    # -------------------------------------------------------------
    unique_orgs = len({env.get("organisation_number") for env in envelopes})
    ux_ratio = 1.0 if unique_orgs == total_companies and contract_violations == 0 else 0.5
    ux_proxy = ux_ratio * 8.0

    total_score = recall_proxy + evidence_proxy + synthesis_proxy + ux_proxy

    return {
        "total_score": round(total_score, 2),
        "components": {
            "recall_proxy": round(recall_proxy, 2),
            "evidence_proxy": round(evidence_proxy, 2),
            "synthesis_proxy": round(synthesis_proxy, 2),
            "ux_proxy": round(ux_proxy, 2),
        },
        "metrics": {
            "total_companies": total_companies,
            "companies_with_facts": companies_with_facts,
            "total_available_claims": total_available_claims,
            "evidence_backed_claims": evidence_backed_claims,
            "unsupported_claims": unsupported_claims,
            "contract_violations": contract_violations,
            "valid_summaries": valid_summaries,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Signalpost Score Proxy")
    parser.add_argument("--envelopes", default="out/envelopes.jsonl", help="Path to envelopes JSONL")
    args = parser.parse_args()

    env_path = Path(args.envelopes)
    if not env_path.exists():
        print(f"Error: {env_path} does not exist.", file=sys.stderr)
        sys.exit(1)

    result = compute_local_proxy_score(env_path)
    comp = result["components"]
    met = result["metrics"]

    print("============================================================")
    print("LOCAL ENGINEERING PROXY — NOT BUILDERR OFFICIAL SCORE")
    print("============================================================")
    print(f"Recall and Coverage:    {comp['recall_proxy']:5.2f} / 50")
    print(f"Precision and Evidence: {comp['evidence_proxy']:5.2f} / 30")
    print(f"Synthesis:              {comp['synthesis_proxy']:5.2f} / 12")
    print(f"UX:                     {comp['ux_proxy']:5.2f} /  8")
    print("------------------------------------------------------------")
    print(f"TOTAL LOCAL PROXY:      {result['total_score']:5.2f} / 100")
    print("============================================================")
    print(f"Companies:              {met['total_companies']}")
    print(f"Companies with >=1 fact:{met['companies_with_facts']}")
    print(f"Available claims:       {met['total_available_claims']}")
    print(f"Evidence backed:        {met['evidence_backed_claims']}")
    print(f"Unsupported claims:     {met['unsupported_claims']}")
    print(f"Contract violations:    {met['contract_violations']}")
    print("============================================================")


if __name__ == "__main__":
    main()
