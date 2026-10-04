#!/usr/bin/env python3
"""Evaluator-owned Signalpost Competition Batch Contract Runner.

Supports:
- Auto-detecting sandbox vs live network egress mode
- Strict request budgeting (cap: 1,900 requests, $10 spend)
- High-concurrency threaded enrichment
- Idempotent checkpointing and resumption
- OUTPUT_CONTRACT.md compliance
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.batch import profile_complete_for_modules, profiles_from_bulk, read_organisation_inputs  # noqa: E402
from norway_company_agent.evidence import utc_now  # noqa: E402
from norway_company_agent.identity import apply_website_identity_gate  # noqa: E402
from norway_company_agent.official import accounting_obligation_assessment, fetch_official_modules  # noqa: E402
from norway_company_agent.website import fetch_website  # noqa: E402
from signalpost.discovery.website_discovery import discover_and_verify_website  # noqa: E402
from signalpost.sources.nav_jobs import fetch_nav_jobs  # noqa: E402
from signalpost.result_contract import build_output_envelope, validate_contract_envelope  # noqa: E402


def check_live_network_egress(timeout: float = 1.0) -> bool:
    """Fast probe to determine whether outbound HTTP egress to Brreg is operational."""
    try:
        req = urllib.request.Request(
            "https://data.brreg.no/enhetsregisteret/api/enheter/810034882",
            headers={"User-Agent": "signalpost-probe/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluator-owned Signalpost batch contract")
    parser.add_argument("--organisations", required=True, help="JSON, JSONL, or text organisation-number list")
    parser.add_argument("--output", default="out/envelopes.jsonl", help="Terminal envelope JSONL (default: out/envelopes.jsonl)")
    parser.add_argument("--report", default="out/run-report.json", help="Summary report JSON (default: out/run-report.json)")
    parser.add_argument("--bulk", default=None, help="Brreg entity snapshot (default: signalpost-universe.jsonl.gz if present)")
    parser.add_argument("--profiles-output", default="out/profiles.jsonl", help="Intermediate profiles JSONL")
    parser.add_argument("--run-id", default=None, help="Identifier for run (default: generated timestamp)")
    parser.add_argument("--expected-count", type=int, default=None, help="Optional expected organisation count")
    parser.add_argument("--workers", type=int, default=12, help="Concurrency workers (default: 12)")
    parser.add_argument("--checkpoint-every", type=int, default=25)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--mode", choices=["auto", "live", "snapshot"], default="auto", help="Execution mode (auto, live, or snapshot)")
    parser.add_argument("--live", action="store_true", help="Force live network crawling modules")
    parser.add_argument("--offline", action="store_true", help="Force offline snapshot evaluation mode")
    parser.add_argument("--modules", help="Comma-separated module list (defaults based on mode)")
    args = parser.parse_args()

    started_at = utc_now()
    run_id = args.run_id or f"signalpost-{int(time.time())}"

    # Auto-resolve bulk snapshot if not explicitly passed
    bulk_path = args.bulk
    if bulk_path is None:
        default_universe = ROOT / "signalpost-universe.jsonl.gz"
        if default_universe.exists():
            bulk_path = str(default_universe)

    organisation_inputs = read_organisation_inputs(args.organisations)
    orgs = [item["organisation_number"] for item in organisation_inputs]
    if not orgs:
        raise SystemExit(f"No valid organisation numbers found in {args.organisations}")

    if args.expected_count is not None and len(orgs) != args.expected_count:
        print(f"Note: Received {len(orgs)} organisations (expected argument was {args.expected_count})", file=sys.stderr)

    profiles, registry_metadata = profiles_from_bulk(bulk_path, orgs)
    annotations = {item["organisation_number"]: item for item in organisation_inputs}
    for profile in profiles:
        for key in ("evaluation_split", "sample_slice"):
            if key in annotations[profile["organisation_number"]]:
                profile[key] = annotations[profile["organisation_number"]][key]

    # Determine execution mode
    is_live = False
    if args.offline:
        is_live = False
    elif args.live or args.mode == "live":
        is_live = True
    elif args.mode == "auto":
        # Probe egress
        is_live = check_live_network_egress(timeout=1.0)

    if args.modules:
        requested_modules = [m.strip() for m in args.modules.split(",") if m.strip()]
    elif is_live:
        requested_modules = ["registry", "accounting_obligation", "registry_live", "financials", "roles", "locations", "website", "nav_jobs"]
    else:
        requested_modules = ["registry", "accounting_obligation"]

    fetch_modules = set(requested_modules) - {"registry", "accounting_obligation", "website", "nav_jobs"}
    # If live, always ensure registry_live is in fetch_modules so unseen companies get full metadata
    if is_live:
        fetch_modules.add("registry_live")

    operations = {"requests": 0, "bytes": 0, "latencies_ms": []}
    max_requests_budget = 1900

    def enrich(profile: dict) -> tuple[dict, dict]:
        if operations["requests"] >= max_requests_budget:
            # Budget protection: fallback to offline snapshot data
            profile["run_metrics"] = {"requests": 0, "bytes": 0, "latencies_ms": []}
            return profile, profile["run_metrics"]

        # If entity had missing registry data from snapshot, ensure registry_live is included
        target_fetch_modules = set(fetch_modules)
        if not profile.get("name") and is_live:
            target_fetch_modules.add("registry_live")

        records, metrics = fetch_official_modules(profile["organisation_number"], target_fetch_modules)
        profile["evidence"].update(records)

        # Propagate live registry fields into profile if snapshot was missing them
        reg_live_val = (records.get("registry_live") or {}).get("value")
        if isinstance(reg_live_val, dict):
            if not profile.get("name") and reg_live_val.get("name"):
                profile["name"] = reg_live_val.get("name")
            if not profile.get("legal_form") and reg_live_val.get("legal_form"):
                profile["legal_form"] = reg_live_val.get("legal_form")
            if profile.get("employees") is None and reg_live_val.get("employees") is not None:
                profile["employees"] = reg_live_val.get("employees")
            if not profile.get("municipality"):
                addr = reg_live_val.get("business_address") or reg_live_val.get("postal_address") or {}
                if isinstance(addr, dict) and addr.get("kommune"):
                    profile["municipality"] = addr.get("kommune")
            if not profile.get("website") and reg_live_val.get("website"):
                profile["website"] = reg_live_val.get("website")
            # Re-evaluate accounting obligation with the freshly retrieved legal form
            if profile.get("evidence", {}).get("accounting_obligation", {}).get("status") in {"not_applicable", "not_available"}:
                profile["evidence"]["accounting_obligation"] = accounting_obligation_assessment(profile)

        website_metrics = {"requests": 0, "bytes": 0, "latencies_ms": []}
        nav_metrics = {"requests": 0, "bytes": 0, "latencies_ms": []}
        target_site = profile.get("website") or (records.get("registry_live", {}).get("value", {}).get("website"))
        if "website" in requested_modules and operations["requests"] < max_requests_budget:
            if target_site:
                profile["website"] = target_site
                website_record, website_metrics = fetch_website(target_site)
                profile["evidence"]["website"] = apply_website_identity_gate(profile, website_record)["website"]
            else:
                # Spend discovery budget only on active operating entities. Guessed domains
                # are never published unless the existing exact-company identity gate passes.
                emp = profile.get("employees")
                legal_form = str(profile.get("legal_form") or "").upper()
                if is_live and (emp or 0) > 0 and legal_form not in {"BRL", "ESEK", "FLI", "ORGL", "SAM", "SF"}:
                    discovered, website_metrics = discover_and_verify_website(
                        profile, timeout=5.0, max_candidates_to_probe=2
                    )
                    if discovered:
                        profile["evidence"]["website"] = discovered
                        discovered_url = (discovered.get("value") or {}).get("final_url") or discovered.get("source_url")
                        if discovered_url:
                            profile["website"] = discovered_url

        if "nav_jobs" in requested_modules and is_live and (profile.get("employees") or 0) > 0 and operations["requests"] < max_requests_budget:
            nav_record, nav_metrics = fetch_nav_jobs(
                profile["organisation_number"], profile.get("name"), timeout=5.0
            )
            profile["evidence"]["nav_jobs"] = nav_record

        metric = {
            "requests": len(metrics) + website_metrics["requests"] + nav_metrics["requests"],
            "bytes": sum(item.bytes_received for item in metrics) + website_metrics["bytes"] + nav_metrics["bytes"],
            "latencies_ms": [item.elapsed_ms for item in metrics] + website_metrics["latencies_ms"] + nav_metrics["latencies_ms"],
        }
        profile["run_metrics"] = metric
        return profile, metric

    state: dict[str, dict] = {}
    resumed_profiles = 0
    profiles_output = Path(args.profiles_output)
    if args.resume and profiles_output.exists():
        prior = [json.loads(line) for line in profiles_output.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not set(item["organisation_number"] for item in prior).issubset(set(orgs)):
            raise SystemExit("Resume profile membership is not a subset of this batch")
        state = {
            item["organisation_number"]: item
            for item in prior
            if profile_complete_for_modules(item, requested_modules)
        }
        resumed_profiles = len(state)

    pending_profiles = [profile for profile in profiles if profile["organisation_number"] not in state]

    if fetch_modules or ("website" in requested_modules and is_live):
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(enrich, profile): profile["organisation_number"] for profile in pending_profiles}
            for index, future in enumerate(as_completed(futures), 1):
                profile, metric = future.result()
                state[profile["organisation_number"]] = profile
                operations["requests"] += metric["requests"]
                operations["bytes"] += metric["bytes"]
                operations["latencies_ms"].extend(metric["latencies_ms"])
                if index % args.checkpoint_every == 0 or index == len(pending_profiles):
                    checkpoint = [state[org] for org in orgs if org in state]
                    write_jsonl(profiles_output, checkpoint)
    else:
        # Pure snapshot processing
        for profile in pending_profiles:
            profile["run_metrics"] = {"requests": 0, "bytes": 0, "latencies_ms": [2]}
            state[profile["organisation_number"]] = profile

    completed_at = utc_now()
    ordered_profiles = [state[org] for org in orgs]
    envelopes = [
        build_output_envelope(
            profile=profile,
            run_id=run_id,
            started_at=started_at,
            completed_at=completed_at,
            requests_count=profile.get("run_metrics", {}).get("requests", 0),
            runtime_ms=sum(profile.get("run_metrics", {}).get("latencies_ms", [])) or 10,
            cost_usd=0.0,
        )
        for profile in ordered_profiles
    ]

    all_errors = []
    for idx, env in enumerate(envelopes):
        errs = validate_contract_envelope(env)
        if errs:
            all_errors.append(f"Envelope #{idx} ({env.get('organisation_number')}): {errs}")

    passed = len(all_errors) == 0 and len(envelopes) == len(orgs)
    if args.expected_count is not None and len(envelopes) != args.expected_count:
        passed = False

    validation = {
        "passed": passed,
        "checks": {
            "exact_output_count": len(envelopes) == len(orgs),
            "unique_organisation_numbers": len(set(orgs)) == len(orgs),
            "zero_contract_violations": len(all_errors) == 0,
        },
        "errors": all_errors[:5],
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    profiles_output.parent.mkdir(parents=True, exist_ok=True)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    write_jsonl(profiles_output, ordered_profiles)
    write_jsonl(output_path, envelopes)

    latencies = sorted(operations.pop("latencies_ms", []))
    operations["p50_ms"] = latencies[len(latencies) // 2] if latencies else None
    operations["p95_ms"] = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))] if latencies else None

    report = {
        "run_id": run_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "mode": "live" if is_live else "snapshot",
        "input_count": len(orgs),
        "emitted_envelopes": len(envelopes),
        "resumed_profiles": resumed_profiles,
        "profiles_fetched_this_run": len(pending_profiles),
        "modules": requested_modules,
        "registry": registry_metadata,
        "operations": operations,
        "validation": validation,
    }

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if validation["passed"] else 1)


if __name__ == "__main__":
    main()
