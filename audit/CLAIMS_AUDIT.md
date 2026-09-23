# Signalpost — Zero-Trust Claim Verification Audit Table

**Audit Date:** 2026-09-23  
**Auditor:** Antigravity Autonomous Zero-Trust Auditor  
**Repository Commit (Baseline):** `918b6042cc3eb9b9c96dbab4e9e15d57d69835b2`  
**Evaluation Standard:** Builderr Signalpost Challenge Contract  

---

## 1. Walkthrough Claims vs Independent Verification

| # | Walkthrough Claim | Evidence Required | Command / Check Used | Observed Result | Verdict | Notes |
| :- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **127 pytest tests pass** | Full pytest execution log with zero failures | `PYTHONPATH=src python3 -m pytest -q` | `127 passed, 5 subtests passed in 2.20s` | **PASS** | Saved to `audit/pytest_baseline.txt`. |
| 2 | **5 subtests pass** | Subtest execution report | `pytest` output inspection | 5 subtests passed | **PASS** | Subtests in `tests/test_poc.py` verified. |
| 3 | **100% refresh precision & recall** | Provenance report with ground truth | Inspected `scratch/.../out/refresh-demo.json` and `scripts/run_refresh_replay.py` | Precision: 1.0, Recall: 1.0 on a **single company (923609016), 2 expected changes** | **PARTIAL** | The claim of "100% precision/recall" is technically true for the 1-profile micro-fixture, but is misleading when presented as a general evaluation metric across 1,000 companies. |
| 4 | **Exactly 100 benchmark envelopes** | Output envelope count and uniqueness check | Parsed `out/envelopes.jsonl` from `run_competition_batch.py` | Exactly 100 envelopes, 100 unique organisation numbers | **PASS** | Matches `data/input/benchmark-100.jsonl` exactly. |
| 5 | **12.63 second benchmark runtime** | Measured wall-clock time in snapshot mode | Ran `scripts/benchmark_100.py` & `scripts/run_competition_batch.py` | `benchmark_100.py`: ~12.6s; `run_competition_batch.py`: 4.77s | **PASS** | Valid in local snapshot mode reading `signalpost-universe.jsonl.gz`. |
| 6 | **0 snapshot-mode requests** | Outbound HTTP request count during snapshot run | Checked `operations.requests` in report and client counter | `operations.requests = 0` | **PASS** | No HTTP requests are made when processing frozen registry universe. |
| 7 | **~350 live-crawl requests** | Live network request logs | Inspected network calls and crawler design | Sandbox blocks live outbound calls; live crawl with 8 workers on 100 companies targets ~2-4 requests/company | **PARTIAL** | Cannot reproduce live crawling inside sandboxed environment without external network egress. |
| 8 | **$0.00 third-party API cost** | Codebase audit for paid API calls and credentials | Grep search for OpenAI, Anthropic, Gemini, SerpAPI, API keys | 0 paid APIs invoked in default evaluator pipeline. Spend is exactly $0.00 | **PASS** | Fully verified in `submission/COST_REPORT.md`. |
| 9 | **0 contract / schema errors** | Schema validation against `OUTPUT_CONTRACT.md` | `validate_contract_envelope(e)` on envelopes | `submission/envelopes.jsonl`: 0 errors. **BUT** `run_competition_batch.py`: 100 schema errors! | **FAIL** (Fixed in P0) | `run_competition_batch.py` previously called legacy starter-kit envelope instead of `signalpost.result_contract`. |
| 10 | **Idempotent rerun (0 false changes)** | Diffing identical consecutive runs | `diff_datasets(profiles, copy.deepcopy(profiles))` | Exactly 0 change events emitted | **PASS** | Verified in `tests/unit/test_refresh_idempotent.py` and benchmark runs. |
| 11 | **1,000 organisation numbers** | Inspection of `submission/organisation_numbers.txt` | Independent python audit script | Exactly 1,000 lines, 1,000 unique, 100% valid Norwegian 9-digit Modulo 11 checksums, 100% in universe | **PASS** | Verified in `audit/organisation_number_audit.json`. |
| 12 | **1,000 profiles** | JSON parsing of every line in `submission/profiles.jsonl` | Line count, unique org numbers, schema check | Exactly 1,000 valid JSON profiles matching manifest 1-to-1 | **PASS** | Zero syntax errors, zero NaN/Inf. |
| 13 | **1,000 terminal envelopes** | JSON parsing of every line in `submission/envelopes.jsonl` | Line count, unique org numbers, contract check | Exactly 1,000 valid envelopes matching manifest 1-to-1 | **PASS** | All required sections present. |
| 14 | **5,000 claims** | Exact count of claim items across all envelopes | Counted `claims` across 1,000 envelopes | Exactly 5,000 claims (5 per company: legal_name, legal_form, employees, annual_revenue, official_website) | **PASS** | Count is exact, but generated from fixed envelope slots. |
| 15 | **Every claim has evidence** | Check that `len(claim['evidence_ids']) > 0` | Inspected `evidence_ids` for all 5,000 claims | 3,000 claims have evidence; **2,000 claims have `evidence_ids: []`** | **FAIL** (Misleading claim) | 2,000 claims represent unobserved/unavailable facts (`annual_revenue`, `official_website`) where `availability == "not_available"`. All 2,144 `available` claims have evidence, but claiming "5,000 claims with evidence" was false. |
| 16 | **Submission validator returns 0 errors** | Execution of `scripts/validate_submission.py` | Ran `python3 scripts/validate_submission.py` | Exited 0 with all checks passed | **PASS** | Ran with zero errors. |
| 17 | **All required submission files exist** | Filesystem check in `submission/` | `ls -la submission/` | All 7 files exist (`organisation_numbers.txt`, `profiles.jsonl`, `envelopes.jsonl`, `PROFILE_STATS.md`, `COST_REPORT.md`, `RUN_INFO.md`, `SUBMISSION_EMAIL.txt`) | **PASS** | Baseline SHA-256 hashes recorded in `audit/baseline_hashes.sha256`. |
| 18 | **Evaluator command really works** | Run command from `submission/RUN_INFO.md` | Ran documented batch command | Stalled due to live module defaults in sandbox | **FAIL** (Fixed in P0) | Command defaulted to live HTTP calls that hung in sandbox. Changing default to snapshot modules or passing `--modules` fixes it. |
| 19 | **Output matches current Builderr contract** | Field-by-field comparison against `OUTPUT_CONTRACT.md` | `audit/CONTRACT_COMPARISON.md` | All fields present and compliant | **PASS** (for `submission/envelopes.jsonl`) | Conformance verified. |
| 20 | **Repository is reproducible from clean environment** | Inspection of dependency definitions | Inspected `pyproject.toml` and installed packages | `httpx` and `pytest` missing from base `pyproject.toml`; no `requirements.txt` | **PARTIAL** (Fixed in P1) | Needs pinned `requirements.txt`. |
