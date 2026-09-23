# Signalpost — Norwegian Company Intelligence Research Agent

[![Builderr Evaluation](https://img.shields.io/badge/Builderr-Qualified-brightgreen)](https://builderr.ai/challenges/signalpost)
[![Tests Passing](https://img.shields.io/badge/Tests-127%20Passed-success)](tests/)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/License-MIT-purple)](LICENSE)

An autonomous, evidence-bounded intelligence agent that receives a Norwegian organisation number, anchors identity in authoritative public registers, discovers permitted company websites, strictly verifies entity attribution, preserves claim-level evidence, and detects temporal updates with idempotent guarantees.

Built for the **[Builderr Signalpost Hackathon](https://builderr.ai/challenges/signalpost)**.

---

## 1. Quick Start: One-Command Evaluator Run

To reproduce the official daily evaluation batch on 100 companies:

```bash
python3 scripts/run_competition_batch.py \
  --organisations data/input/benchmark-100.jsonl \
  --bulk data/input/signalpost-universe.jsonl.gz \
  --profiles-output out/profiles.jsonl \
  --output out/envelopes.jsonl \
  --report out/run-report.json \
  --run-id eval-001 \
  --expected-count 100
```

To research a single Norwegian company from the CLI:

```bash
python3 -m signalpost research --org-number 985589003
```

---

## 2. Architecture & Pipeline

```
Norwegian Organisation Number (9 digits)
   │
   ▼
[1. Official Identity Anchor] ───────► Brønnøysundregistrene (Enhetsregisteret)
   │                                   • Legal Name, Org Form, Address, Municipality
   ▼                                   • Workforce Count, Accounting Obligation
[2. Source Planner & Budget] ────────► Safe Request Budget (Max 1,900 Reqs, $10 Cost)
   │
   ▼
[3. Domain & Source Discovery] ──────► Official Declared Website / Priority Subpages
   │
   ▼
[4. Strict Entity Resolution Gate] ──► Hard Rejection on Conflicting Org Number
   │                                   • Token Overlap & Distinctive Legal Name Scoring
   ▼
[5. Safe Fetcher & Cache] ───────────► SSRF Filter (Blocks loopback/RFC1918/metadata)
   │                                   • SHA-256 Content-Addressed On-Disk Cache
   ▼
[6. Deterministic Fact Extraction] ──► Structured JSON-LD / Microdata
   │                                   • Financials (NOK scale factor normalization)
   │                                   • Leadership (Roles: Daglig leder, Styreleder)
   │                                   • Workplaces (Subunits & operational offices)
   ▼
[7. Evidence Grounding & Hashes] ────► URL + Retrieval Timestamp + Content SHA-256
   │
   ▼
[8. Idempotent Diff & Refresh] ──────► Semantic Fact Fingerprints (Zero False Changes)
   │                                   • Source errors recorded as unobserved, NOT removals
   ▼
[9. Evidence Brief Synthesis] ───────► Deterministic brief without hallucinations
   │
   ▼
[10. Terminal Result Envelope] ──────► Exact Builderr OUTPUT_CONTRACT.md Conformance
```

---

## 3. Observed 100-Company Benchmark Results

Measured on macOS (Apple M-series, Python 3.14.3) across 100 official Norwegian entities:

| Metric | Measured Result | Evaluator Cap | Status |
| :--- | :--- | :--- | :--- |
| **Terminal Envelopes** | **Exactly 100** | Exactly 100 | **PASS** |
| **Wall-Clock Duration** | **12.63 seconds** | <= 45 minutes (2,700s) | **PASS** |
| **Per-Company Latency (p50)** | **0 ms** (Cached/snapshot) | - | **PASS** |
| **Per-Company Latency (p95)** | **0 ms** (Cached/snapshot) | <= 10,000 ms | **PASS** |
| **Outbound HTTP Requests** | **0** (Snapshot mode) / **~350** (Live crawl) | <= 2,000 requests | **PASS** |
| **Declared External API Cost** | **$0.00** | <= $10.00 | **PASS ($0.00)** |
| **Schema Validation Errors** | **0 errors** | Zero schema errors | **PASS** |
| **Idempotent Refresh** | **0 false changes** | Zero duplicate records | **PASS** |

---

## 4. Key Differentiators & Safeguards

### Exact Company Identity (Zero Wrong-Company Tolerance)
- A material wrong-company publication results in immediate disqualification.
- A candidate domain is **never** accepted based on name similarity alone.
- **Hard Rejection**: If a web page presents a conflicting 9-digit Norwegian organisation number, it is instantly rejected (`score = 0.0`).
- **Verified Status**: A website is accepted only if the target organisation number appears on the site, or all distinctive legal name tokens match with substantive business content (`score >= 0.90`).

### Financial Extraction & Anti-Fabrication Safeguards
- Financial figures are extracted strictly from statutory filings.
- **Scale Normalization**: Automatically detects and normalizes scale notes (e.g. `i hele tusen NOK`, `MNOK`) to base NOK currency.
- **Negative Sign Handling**: Correctly parses Norwegian accounting conventions, including negative profits denoted in parentheses (e.g. `(25 400)` $\rightarrow$ `-25400`).
- **Zero-Tolerance for Imputation**: Missing financial numbers **never** become zero. If unobserved, they are recorded as `None` with availability `not_available` or `not_applicable`.

### SSRF Defense & URL Security
- Every outbound request passes through `assert_public_url()`.
- Rejects non-HTTP schemes (`file://`, `ftp://`, `gopher://`, `data:`).
- Rejects loopback (`127.0.0.0/8`, `::1`), RFC1918 private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), and cloud metadata IP (`169.254.169.254`).
- Validates every hop in redirect chains.

### Idempotent Refresh & Historical Evidence Preservation
- Rerunning the agent against identical source snapshots produces **zero duplicate facts** and **zero false change events**.
- Real-world changes (e.g. new CEO, updated filing year, workforce changes) emit typed change events (`role_changed`, `financial_update`, `workforce_updated`).
- Prior evidence records and content hashes are permanently retained.
- Transient network errors (404/500/timeout) are recorded as `source_error`, never as confirmed business removals.

---

## 5. Permitted Sources & Rights

Signalpost exclusively accesses lawful, public, auditable sources:
1. **Brønnøysundregistrene Enhetsregisteret & Regnskapsregisteret**: Public Norwegian government register under Norwegian Licence for Open Government Data (NLOD).
2. **Verified Company Websites**: Publicly accessible web pages subject to `robots.txt` compliance, polite rate limits, and concurrency caps.
3. **Embedded Schema.org Structured Data**: Directly extracted from company-owned pages.

*Policy on Restricted Platforms:* In compliance with Builderr rules, Signalpost does not scrape LinkedIn, Meta, Indeed, or Glassdoor without authorized official APIs.

---

## 6. Testing & Quality Verification

Run the comprehensive test suite (127 unit, security, and regression tests):

```bash
# Full test suite:
PYTHONPATH=src python3 -m pytest -q

# Official refresh replay fixture:
python3 scripts/run_refresh_replay.py \
  --manifest tests/fixtures/refresh-snapshots.json \
  --output out/refresh-demo.json

# 100-company evaluation benchmark:
python3 scripts/benchmark_100.py

# Submission package integrity validator:
python3 scripts/validate_submission.py \
  --manifest submission/organisation_numbers.txt \
  --envelopes submission/envelopes.jsonl \
  --profiles submission/profiles.jsonl
```

---

## 7. Submission Artifacts

The final submission package is frozen in `submission/`:
- **`submission/organisation_numbers.txt`**: 1,000 valid, unique Norwegian organisation numbers.
- **`submission/profiles.jsonl`**: 1,000 completed company profiles.
- **`submission/envelopes.jsonl`**: 1,000 terminal envelopes conforming to `OUTPUT_CONTRACT.md`.
- **`submission/PROFILE_STATS.md`**: Statistical breakdown across legal forms, industries, and regions.
- **`submission/COST_REPORT.md`**: Itemized cost report ($0.00 standard run).
- **`submission/RUN_INFO.md`**: Run parameters, commit hash, runtime specifications.
- **`submission/SUBMISSION_EMAIL.txt`**: Submission email draft.

---

## 8. Interactive Verification UI

To inspect the 100-company interactive showcase on desktop or mobile:

```bash
python3 scripts/serve_ui.py
# Open http://localhost:8080/showcase.html in your browser
```

---

## 9. License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
