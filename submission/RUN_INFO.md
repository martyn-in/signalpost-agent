# Signalpost Run & Submission Specification

**Challenge:** Signalpost — Build an Agent That Finds Company Information  
**Official Evaluator Contract:** [Builderr Evaluation Harness v2](https://builderr.ai/docs/signalpost-evaluation-harness.md)  
**Agent Name:** Signalpost Norwegian Company Research Agent  

---

## Submission Details

- **Repository Remote:** `<Configured by submitter; see git remote -v>`
- **Exact Commit Hash:** `[Generated after final commit freeze via 'git rev-parse HEAD']`
- **Completed Profiles Count:** 1,000 completed company profiles
- **Completed Profiles Path:** `submission/profiles.jsonl`
- **Organisation Numbers Manifest:** `submission/organisation_numbers.txt`
- **Terminal Envelopes Path:** `submission/envelopes.jsonl`
- **Statistics Report:** `submission/PROFILE_STATS.md`
- **Cost Report:** `submission/COST_REPORT.md`
- **Runtime Environment:** Python 3.12+ (tested on Python 3.14.3 macOS/Linux)

---

## One Reproducible Evaluator Run Command

The evaluator can execute the official daily 100-company evaluation run using:

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

*Note: For single-company research, use:*
```bash
python3 -m signalpost research --org-number 985589003
```

---

## Verification & Benchmark Commands

```bash
# 1. Run full test suite (129 tests + subtests):
PYTHONPATH=src python3 -m pytest -q

# 2. Run 100-company benchmark:
python3 scripts/benchmark_100.py

# 3. Validate submission package:
python3 scripts/validate_submission.py \
  --manifest submission/organisation_numbers.txt \
  --envelopes submission/envelopes.jsonl \
  --profiles submission/profiles.jsonl
```

---

## Operational Specifications

- **Models Used:** Deterministic rule-based extractors, structured JSON-LD / Microdata parsers, BeautifulSoup, and Regex. (Zero mandatory LLM dependencies; optional `LLM_API_KEY` for summarization).
- **APIs Used:** Public Brønnøysundregistrene (Enhetsregisteret & Regnskapsregisteret); direct safe HTTP crawling.
- **Licensing & Rights:** All sources accessed conform to public Norwegian government data licenses (NLOD) and public web terms.
- **Expected Cost per 100-Company Run:** **$0.00** (Well below the $10.00 competition limit).
- **Observed Requests per 100-Company Run:** 0 (frozen registry snapshot mode) to < 450 (live web crawling mode), well within the 2,000 request limit.
