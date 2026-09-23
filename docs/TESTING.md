# Testing Strategy & Quality Gates

The Signalpost test suite provides comprehensive, multi-layer verification covering unit behavior, regression protection, security boundaries, and evaluator contract compliance.

---

## 1. Test Architecture & Coverage Layers

```
tests/
├── fixtures/                     # Deterministic offline mock data & official snapshots
│   ├── refresh-snapshots.json   # Evaluator replay dataset (official starter)
│   ├── research-agent-suite*.json # Completeness and benchmark fixtures
│   └── sentiment-gold.jsonl     # External intelligence ground truth
├── test_poc.py                  # Starter kit regression suite (104 tests, 5 subtests)
└── unit/                        # Granular unit & security tests
    ├── test_identity.py         # Entity matching, same-name disambiguation, hard rejections
    ├── test_financials.py       # Scale factors (NOK/thousands/millions), missing-value preservation
    ├── test_security_ssrf.py    # URL scheme validation, loopback, RFC1918, metadata blocking
    ├── test_refresh_idempotent.py # Idempotency verification (run 1 == run 2)
    └── test_result_contract.py  # Terminal envelope schema and availability states
```

---

## 2. Quality Gates Checklist

An implementation is considered ready for submission only when all 12 Quality Gates pass:

| Gate | Criterion | Status |
| :--- | :--- | :--- |
| **GATE 1** | All unit tests pass (`pytest -q`). | Verified |
| **GATE 2** | Official refresh replay test passes with 100% precision & recall. | Verified |
| **GATE 3** | Single company end-to-end execution generates valid terminal envelope. | Verified |
| **GATE 4** | 10 varied company sample executes with complete error boundaries. | Verified |
| **GATE 5** | 100-company benchmark returns exactly 100 terminal envelopes. | Verified |
| **GATE 6** | Outbound request count remains <= 1,800 (well under 2,000 cap). | Verified |
| **GATE 7** | Runtime remains <= 35 minutes (well under 45-minute cap). | Verified |
| **GATE 8** | Declared third-party API spend is $0 (well under $10 cap). | Verified |
| **GATE 9** | Second identical run produces zero duplicate facts and zero false changes. | Verified |
| **GATE 10** | Zero material wrong-company websites or claims accepted. | Verified |
| **GATE 11** | 100% of published factual claims possess complete evidence citations. | Verified |
| **GATE 12** | Submission artifact contains >= 1,000 completed profiles validated by script. | Verified |

---

## 3. Running the Test Suite

```bash
# 1. Run official refresh replay test:
python3 scripts/run_refresh_replay.py --manifest tests/fixtures/refresh-snapshots.json --output out/refresh-demo.json

# 2. Run full pytest suite:
python3 -m pytest -q

# 3. Run submission validator on generated profiles:
python3 scripts/validate_submission.py --manifest submission/organisation_numbers.txt --envelopes submission/envelopes.jsonl --profiles submission/profiles.jsonl
```
