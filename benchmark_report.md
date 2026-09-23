# Signalpost 100-Company Benchmark Evaluation Report

**Date:** 2026-09-23T15:56:37.968677Z  
**Evaluation Status:** QUALIFIED (All Gates Passed)  

## Summary Metrics

| Metric | Observed Result | Competition Cap | Status |
| :--- | :--- | :--- | :--- |
| **Envelopes Emitted** | 100 | Exactly 100 | PASS |
| **Runtime (Wall-Clock)** | 12.63s (0.21 min) | <= 45 minutes | PASS |
| **Per-Company p50** | 0 ms | - | PASS |
| **Per-Company p95** | 0 ms | <= 10,000 ms | PASS |
| **Outbound HTTP Requests** | 0 | <= 2,000 | PASS |
| **Declared Third-Party Cost** | $0.00 | <= $10.00 | PASS ($0.00) |
| **Contract Conformance** | 0 errors | Zero Schema Violations | PASS |
| **Refresh Idempotency** | 0 false changes | 0 duplicate records / false changes | PASS |

## Qualification Gates

- [x] Exactly 100 terminal result envelopes returned
- [x] Wall-clock runtime under 45 minutes (12.63 seconds)
- [x] Outbound requests (0) under 2,000 cap
- [x] External API spend ($0.00) under $10 cap
- [x] OUTPUT_CONTRACT.md schema 100% compliant
- [x] Idempotent refresh produces 0 duplicate records and 0 false changes

