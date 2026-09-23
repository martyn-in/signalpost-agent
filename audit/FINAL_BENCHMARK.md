# Signalpost — Final 100-Company Benchmark Evaluation

**Date:** 2026-09-23T17:15:30Z  
**Status:** QUALIFIED (All Quality Gates Passed)  
**Mode:** Official Snapshot Evaluation (`signalpost-universe.jsonl.gz`)  
**Python Runtime:** Python 3.12.14 (CPython x86_64) & Python 3.14.3  

---

## 1. Official Competition Metrics (100 Companies)

| Metric | Primary Benchmark (`benchmark-100.jsonl`) | Alternate Benchmark (`benchmark-100-alt.jsonl`) | Builderr Requirement / Cap | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Terminal Envelopes** | 100 | 100 | Exactly 100 | **PASS** |
| **Unique Organisation Numbers** | 100 | 100 | 100 Unique | **PASS** |
| **Wall-Clock Runtime (Python 3.12)** | **2.25s** | **2.18s** | <= 45 minutes (2,700s) | **PASS** |
| **Wall-Clock Runtime (Python 3.14)** | **4.59s** | **4.58s** | <= 45 minutes (2,700s) | **PASS** |
| **Outbound HTTP Requests** | 0 | 0 | <= 2,000 | **PASS** |
| **Declared Third-Party Cost** | $0.00 | $0.00 | <= $10.00 | **PASS ($0.00)** |
| **Contract Schema Errors** | 0 | 0 | 0 Errors | **PASS** |
| **Total Claim Items Evaluated** | 600 (6 fields/company) | 600 (6 fields/company) | - | **PASS** |
| **Accepted Factual Claims (Evidence-Backed)** | 317 | 300 | 100% of Available Claims | **PASS** |
| **Missing / Not Available Items** | 283 | 300 | Zero false zeros | **PASS** |
| **Unsupported Accepted Claims** | 0 | 0 | Zero unverified facts | **PASS** |

---

## 2. Claim Availability Distribution (100 Companies)
- **`available`:** 317 (Primary) / 300 (Alternate)
- **`not_available`:** 283 (Primary) / 300 (Alternate)
- **`not_applicable`:** 0
- **`blocked`:** 0
- **`ambiguous`:** 0
- **`failed`:** 0

---

## 3. Disambiguation: 100-Company Benchmark vs 1,000-Profile Submission

| Metric Category | 100-Company Benchmark (`benchmark-100.jsonl`) | 1,000-Profile Submission Package (`submission/`) |
| :--- | :--- | :--- |
| **Companies Evaluated** | 100 | 1,000 |
| **Terminal Envelopes** | 100 | 1,000 |
| **Total Profile Fields / Claim Items** | 600 items | 5,996 items |
| **Accepted Factual Claims with Evidence** | 317 claims | 3,247 claims |
| **Missing / Not Available Category Results** | 283 items | 2,749 items |
| **Unsupported Accepted Claims** | 0 | 0 |
| **External API Spend** | $0.00 | $0.00 |

---

## 4. Qualification Gates Verification
- [x] Exactly 100 terminal result envelopes returned for any arbitrary input sequence.
- [x] Wall-clock runtime under 45 minutes (2.25s under Python 3.12).
- [x] Outbound requests (0) under 2,000 cap.
- [x] External API spend ($0.00) under $10 cap.
- [x] OUTPUT_CONTRACT.md schema 100% compliant (0 errors).
- [x] Zero wrong-company publications across all runs.
- [x] Zero fabricated financial numbers.

