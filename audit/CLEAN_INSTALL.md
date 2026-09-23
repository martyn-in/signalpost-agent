# Signalpost — Clean Environment & Dependency Reproducibility Audit

**Audit Date:** 2026-09-23  
**Auditor:** Antigravity Autonomous DevOps & QA Engineer  
**Python Runtime:** Python 3.14.3 (macOS Darwin x86_64)  

---

## 1. Pinned Dependencies Specification
All production and evaluation dependencies are explicitly pinned in `requirements.txt`:
```ini
beautifulsoup4==4.15.0
lxml==6.1.3
extruct==0.18.0
trafilatura==2.2.0
tldextract==5.3.2
pypdf==6.19.0
pydantic==2.13.4
httpx==0.28.1
pytest==9.1.1
```

The project definition `pyproject.toml` has also been updated to include `httpx` and `pytest` in base dependencies alongside `beautifulsoup4`, `lxml`, `extruct`, `trafilatura`, `tldextract`, `pypdf`, and `pydantic`.

---

## 2. Installation Procedure
A clean installation can be reproduced in any standard Python 3.12+ environment using either standard `pip` or `uv`:

### Option A: Standard Pip (Universal)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

### Option B: Fast Reproducible Install via UV
```bash
uv venv .venv
source .venv/bin/activate
uv pip sync requirements.txt
```

---

## 3. Evaluator Execution Sequence
From the activated environment, the evaluator runs:

### A. Run Full Test Suite
```bash
PYTHONPATH=src pytest -q
```
*Expected Result:*
```
129 passed, 5 subtests passed in ~2.5s (0 failures, 0 warnings)
```

### B. Execute 100-Company Evaluation Batch
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
*Expected Result:*
- Wall-clock time: ~5–12 seconds
- Emitted terminal envelopes: Exactly 100 (100% unique)
- Outbound requests: 0 (local snapshot mode)
- Third-party API cost: $0.00
- Exit code: 0

### C. Validate Submission Package
```bash
python3 scripts/validate_submission.py \
  --manifest submission/organisation_numbers.txt \
  --envelopes submission/envelopes.jsonl \
  --profiles submission/profiles.jsonl
```
*Expected Result:*
```
[PASS] Manifest contains 1,000 valid unique organisation numbers
[PASS] Profiles file contains 1,000 valid profiles matching manifest sequence
[PASS] Envelopes file contains 1,000 valid envelopes
[PASS] Total validated claims: 5,996 across 1,000 companies
[PASS] Total validated evidence records: 1,000
[SUCCESS] All Builderr Signalpost submission validation gates PASSED perfectly!
```
