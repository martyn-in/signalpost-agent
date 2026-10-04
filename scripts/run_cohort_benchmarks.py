#!/usr/bin/env python3
"""Run multi-cohort benchmarks across disjoint cohorts A-E and shadow cohort."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.coverage_dashboard import analyze_envelopes
from scripts.local_score_proxy import compute_local_proxy_score


def run_cohort(cohort_name: str, input_path: Path, out_dir: Path) -> dict:
    envelopes_path = out_dir / f"{cohort_name}_envelopes.jsonl"
    report_path = out_dir / f"{cohort_name}_report.json"
    csv_path = out_dir / f"{cohort_name}_coverage.csv"

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_competition_batch.py"),
        "--organisations",
        str(input_path),
        "--output",
        str(envelopes_path),
        "--report",
        str(report_path),
    ]

    t0 = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    elapsed = time.time() - t0

    if res.returncode != 0:
        print(f"Cohort {cohort_name} failed:\n{res.stderr}", file=sys.stderr)
        raise RuntimeError(f"Cohort {cohort_name} failed")

    proxy = compute_local_proxy_score(envelopes_path)
    coverage = analyze_envelopes(envelopes_path, csv_path)

    # Read operational stats
    rep = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    reqs = rep.get("operations", {}).get("requests", 0)

    return {
        "cohort": cohort_name,
        "runtime_s": round(elapsed, 2),
        "requests": reqs,
        "proxy_score": proxy["total_score"],
        "components": proxy["components"],
        "coverage": coverage["metrics"],
        "available_claims": coverage["availability_breakdown"]["available"],
        "envelopes_path": str(envelopes_path),
    }


def main() -> None:
    out_dir = ROOT / "out" / "cohort_benchmarks"
    out_dir.mkdir(parents=True, exist_ok=True)

    cohorts = ["cohort_a", "cohort_b", "cohort_c", "cohort_d", "cohort_e"]
    results = []

    print("============================================================")
    print("RUNNING 5 DISJOINT 100-COMPANY COHORT BENCHMARKS (A-E)")
    print("============================================================")

    for c in cohorts:
        in_path = ROOT / "data" / "input" / "cohorts" / f"{c}.jsonl"
        print(f"\nRunning {c.upper()} ({in_path.name})...")
        res = run_cohort(c, in_path, out_dir)
        results.append(res)
        print(
            f"  Score: {res['proxy_score']:5.2f} / 100 "
            f"(Recall: {res['components']['recall_proxy']}, Ev: {res['components']['evidence_proxy']}, "
            f"Synth: {res['components']['synthesis_proxy']}, UX: {res['components']['ux_proxy']}) "
            f"| Time: {res['runtime_s']}s | Reqs: {res['requests']}"
        )

    # Calculate statistics across A-E
    scores = [r["proxy_score"] for r in results]
    mean_score = sum(scores) / len(scores)
    worst_cohort = min(results, key=lambda r: r["proxy_score"])

    # Run Shadow Cohort (Cohort F)
    shadow_in = ROOT / "data" / "input" / "cohorts" / "cohort_shadow.jsonl"
    print("\nRunning SHADOW COHORT (generalization test)...")
    shadow_res = run_cohort("cohort_shadow", shadow_in, out_dir)
    print(
        f"  Shadow Score: {shadow_res['proxy_score']:5.2f} / 100 "
        f"(Recall: {shadow_res['components']['recall_proxy']}, Ev: {shadow_res['components']['evidence_proxy']}, "
        f"Synth: {shadow_res['components']['synthesis_proxy']}, UX: {shadow_res['components']['ux_proxy']}) "
        f"| Time: {shadow_res['runtime_s']}s"
    )

    summary = {
        "cohorts": results,
        "mean_score": round(mean_score, 2),
        "worst_score": worst_cohort["proxy_score"],
        "worst_cohort": worst_cohort["cohort"],
        "shadow_cohort": shadow_res,
    }

    summary_file = out_dir / "multi_cohort_summary.json"
    summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n============================================================")
    print("MULTI-COHORT BENCHMARK RESULTS")
    print("============================================================")
    for r in results:
        print(f"Cohort {r['cohort'][-1].upper()}:  {r['proxy_score']:5.2f} / 100  (Time: {r['runtime_s']}s, Reqs: {r['requests']})")
    print("------------------------------------------------------------")
    print(f"Mean Score:     {mean_score:5.2f} / 100")
    print(f"Worst Cohort:   {worst_cohort['cohort'].upper()} ({worst_cohort['proxy_score']:5.2f} / 100)")
    print(f"Shadow Cohort:  {shadow_res['proxy_score']:5.2f} / 100")
    print("============================================================")


if __name__ == "__main__":
    main()
