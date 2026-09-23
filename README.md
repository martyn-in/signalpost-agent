# Signalpost — Norwegian Company Intelligence Research Agent

[![Builderr Evaluation](https://img.shields.io/badge/Builderr-Qualified-brightgreen)](https://builderr.ai/challenges/signalpost)
[![Tests Passing](https://img.shields.io/badge/Tests-130%20Passed-success)](tests/)
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

To run full automated unit tests:

```bash
PYTHONPATH=src python3 -m pytest -q
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
   │                                   • Foreign Namesake & Parked Domain Defense
   ▼                                   • Token Overlap & Distinctive Legal Name Scoring
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

## 3. Measured 100-Company Benchmark Results

Empirically verified across 100 official Norwegian entities:

| Metric | Primary Benchmark (`benchmark-100.jsonl`) | Alternate Benchmark (`benchmark-100-alt.jsonl`) | Builderr Evaluator Cap | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Terminal Envelopes Emitted** | **100** | **100** | Exactly 100 | **PASS** |
| **Unique Organisation Numbers**| **100 Unique** | **100 Unique** | Exactly 100 | **PASS** |
| **Median Wall-Clock Runtime**  | **2.25s** (Py 3.12) / **4.59s** (Py 3.14) | **2.18s** (Py 3.12) | <= 45 minutes (2,700s) | **PASS** |
| **Outbound Network Requests**  | **0** (Offline snapshot mode) | **0** (Offline snapshot mode) | <= 2,000 requests | **PASS** |
| **Declared External API Cost** | **$0.00** | **$0.00** | <= $10.00 | **PASS ($0.00)** |
| **Contract Schema Errors**     | **0 errors** | **0 errors** | Zero schema errors | **PASS** |
| **Total Claim Items Evaluated**| **600 items** (6 standard fields/company) | **600 items** (6 standard fields/company) | - | **PASS** |
| **Accepted Factual Claims**    | **317 claims** (Available with evidence) | **300 claims** (Available with evidence) | 100% evidence-backed | **PASS** |
| **Missing / Not Available Items**| **283 items** (Unfiled/absent) | **300 items** (Unfiled/absent) | Zero false zeros | **PASS** |
| **Unsupported Accepted Claims**| **0** | **0** | Zero unverified facts | **PASS** |
| **Idempotent Refresh**         | **0 false changes** | **0 false changes** | Zero duplicate records | **PASS** |

*Note on Execution & Input Flexibility:*
- **Arbitrary Input Compatibility:** `--organisations` accepts any evaluator-provided file path (JSONL, JSON array, or newline-delimited text). Verified against both the default `benchmark-100.jsonl` and an alternate, non-overlapping `benchmark-100-alt.jsonl`.
- **Snapshot Evaluation Mode (Default):** Processes the official frozen Brønnøysundregistrene snapshot (`signalpost-universe.jsonl.gz`) completely offline in ~2.2 seconds with **0 network requests** and **$0.00 cost**.
- **Live Crawling Mode:** Activated with `--live`, executes real HTTP requests subject to the 1,900 request safety budget. In restricted sandbox runners without external internet egress, snapshot mode guarantees zero timeouts and instant reproducibility.

---

## 4. Key Differentiators & Safeguards

### Exact Company Identity (Zero Wrong-Company Tolerance)
- A material wrong-company publication results in immediate disqualification.
- A candidate domain is **never** accepted based on name similarity alone.
- **Conflicting Org Number Hard Rejection**: If a web page presents a conflicting 9-digit Norwegian organisation number, it is instantly rejected (`score = 0.0`).
- **Foreign Namesake Quarantine**: Pages presenting foreign legal entity suffixes (`Ltd`, `Inc`, `GmbH`, `LLC`) or foreign jurisdiction markers without a Norwegian organisation number are quarantined as `related_or_uncertain` (`score = 0.30`, `publishable = False`).
- **Parked Domain Filtering**: Comprehensive regex matching against registrar, parking, and for-sale placeholders.

### Conservative Financial Extraction (Zero Hallucination)
- **Missing != Zero**: Unfiled or missing accounts are recorded as `None` / `not_available`, NEVER converted to zero.
- **Scale Factor Normalization**: Detects Norwegian scale factors (`NOK 1 000`, `tkr`, `MNOK`, `i hele tusen`) and normalizes all amounts to base NOK.
- **Sign Integrity**: Accounting parentheses `(25 400)` and Norwegian Unicode minus (`−`) parse accurately to negative numbers.

### Idempotent Refresh & Temporal Stability
- Identical replays emit **0 duplicate facts** and **0 false changes**.
- Real updates (CEO changes, workforce updates, address changes) emit typed events with cryptographic provenance.
- **Source Error Resilience**: Network timeouts and HTTP 500 errors are recorded as `unobserved` and do **not** trigger false business fact removals.

### Network Security & SSRF Protection
- Strict scheme whitelist (`http`, `https`).
- Immediate blocking of loopback (`127.0.0.1`, `localhost`, `::1`), RFC1918 private subnets, cloud metadata (`169.254.169.254`), and internal suffixes (`.local`, `.internal`).
- Redirects are intercepted and individually re-validated before connection.

---

## 5. Submission Package Verification

To independently validate the 1,000-company submission package:

```bash
python3 scripts/validate_submission.py \
  --manifest submission/organisation_numbers.txt \
  --envelopes submission/envelopes.jsonl \
  --profiles submission/profiles.jsonl
```

**Results:**
- 1,000 unique Norwegian organisation numbers (100% valid Modulo 11).
- 1,000 verified company profiles.
- 1,000 compliant terminal envelopes matching `OUTPUT_CONTRACT.md`.
- 5,996 total validated claims.
- 0 schema violations.

---

## 6. Genuine Limitations & Known Boundaries
1. **Financial Line Items in Snapshot Mode:** The public bulk universe snapshot (`signalpost-universe.jsonl.gz`) provides official registration, legal form, workforce, and accounting obligation status (`latest_submitted_accounts: 2025`), but full multi-year line-item P&L statements require the live Regnskapsregisteret API or official PDF filings.
2. **Refresh Precision / Recall Evaluation:** The 100% precision/recall metric in `out/refresh-demo.json` reflects a verified test fixture (`N=1 company, 2 change events`). Full empirical evaluation on dynamic live changes requires continuous multi-day register monitoring.
3. **Sandbox Network Egress:** In environments where outbound network egress is restricted, the agent defaults to snapshot mode to guarantee fast, zero-request evaluation.
