# Signalpost — Final 100-Company Benchmark Evaluation

**Date:** 2026-09-23T16:28:53.140075Z  
**Status:** QUALIFIED (All Quality Gates Passed)  
**Mode:** Official Snapshot Evaluation (`signalpost-universe.jsonl.gz`)  

---

## 1. Official Competition Metrics

| Metric | Observed Value | Builderr Requirement / Cap | Status |
| :--- | :--- | :--- | :--- |
| **Terminal Envelopes** | 100 | Exactly 100 | **PASS** |
| **Unique Organisation Numbers** | 100 | 100 Unique | **PASS** |
| **Wall-Clock Runtime (Median)** | 4.59s | <= 45 minutes (2,700s) | **PASS** |
| **Outbound HTTP Requests** | 0 | <= 2,000 | **PASS** |
| **Declared Third-Party Cost** | $0.00 | <= $10.00 | **PASS ($0.00)** |
| **Contract Schema Errors** | 0 | 0 Errors | **PASS** |
| **Total Published Claims** | 600 | - | **PASS** |
| **Claims per Company (Avg)** | 6.0 | - | **PASS** |
| **Claims with Cryptographic Evidence**| 317 | 100% of Available Claims | **PASS** |

---

## 2. Claim Availability Distribution (100 Companies)
- **`available`:** 317
- **`not_available`:** 283
- **`not_applicable`:** 0
- **`blocked`:** 0
- **`ambiguous`:** 0
- **`failed`:** 0

---

## 3. Qualification Gates Verification
- [x] Exactly 100 terminal result envelopes returned.
- [x] Wall-clock runtime under 45 minutes (4.59s).
- [x] Outbound requests (0) under 2,000 cap.
- [x] External API spend ($0.00) under $10 cap.
- [x] OUTPUT_CONTRACT.md schema 100% compliant (0 errors).
- [x] Zero wrong-company publications.
- [x] Zero fabricated financial numbers.
