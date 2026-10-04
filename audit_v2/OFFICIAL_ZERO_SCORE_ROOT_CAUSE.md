# Root Cause Analysis: Official 0 Recall / 0 Evidence Evaluation Failure

**Date:** 2026-10-04  
**Target:** Theoretical Maximum 100/100 (50 Recall, 30 Evidence, 12 Synthesis, 8 UX)  
**Evaluated Commit:** `585d0aced4631bbc7934eb99e1675c2a7cb61d80` (V1 Frozen Submission)  
**Status:** ROOT CAUSES IDENTIFIED & REPRODUCED LOCALLY  

---

## Executive Summary

The official evaluation score of **Recall: 0 / 50** and **Evidence: 0 / 30** was **NOT caused by research extraction quality**. It was caused by catastrophic runtime contract and CLI invocation failures that prevented the evaluator from receiving valid verified claim envelopes:

1. **CLI Parameter Rejection (Exit Code 2):** Builderr executes entrant agents with standard three-argument invocations:  
   `python3 scripts/run_competition_batch.py --organisations <INPUT> --output <OUTPUT> --report <REPORT>`  
   In V1, `--bulk`, `--profiles-output`, and `--run-id` were defined with `required=True`. Invoking the script without these arguments immediately caused `argparse` to crash with exit code 2 before processing any company.

2. **Hardcoded Batch Count Crash (Exit Code 1):** In V1, line 53 enforced:  
   `if len(orgs) != args.expected_count: raise SystemExit(f"Expected {args.expected_count} organisations, received {len(orgs)}")`  
   Builderr's official evaluation batch contains **1,000 companies** (expanding to 1,100). When Builderr supplied 1,000 companies, the agent crashed instantly with `SystemExit: Expected 100 organisations, received 1000`. Exactly zero envelopes were emitted.

3. **Missing Live Network Execution by Default:** In the V1 submission email, the documented command omitted `--live`. In V1, omitting `--live` caused the batch runner to run in `snapshot` mode with `fetch_modules = set()` (an empty set of live modules). It made zero network requests.

4. **Snapshot Whitelist Blind Spot:** In snapshot mode, any company not in the bundled `signalpost-universe.jsonl.gz` returned dummy `None` fields. Every single claim was marked `not_available`, producing 0 verified facts and 0 evidence objects.

---

## Forensic Answers to the 10 Mandatory Questions

### 1. Can a completely arbitrary Builderr-supplied input file be passed to our command?
**In V1: NO (FAILED).**  
V1 required `--bulk`, `--profiles-output`, `--run-id`, and `--expected-count 100`. Passing an arbitrary file failed unless all supplementary flags matched V1's rigid assumptions.  
**Required V2 Fix:** Accept arbitrary input paths via `--organisations` (or positional), support all input formats (plain text list of 9-digit org numbers, JSON array `["..."]`, JSON object `{"organisation_numbers": [...]}`, JSONL `{"organisation_number": "..."}`), and automatically provide sensible defaults for `--output`, `--report`, `--profiles-output`, and `--run-id`.

### 2. Does the agent research those exact companies?
**In V1: NO (FAILED).**  
If the supplied companies were not present in the local snapshot `signalpost-universe.jsonl.gz`, V1 emitted empty dummy records with `not_available` on every field without conducting live research.  
**Required V2 Fix:** Dynamic live fallback: The agent checks local snapshot cache first for maximum speed, and for any company not found, it queries the live official Brønnøysundregistrene APIs (`/enheter`, `/regnskap`, `/roller`, `/underenheter`) and official company websites in real-time.

### 3. Does it return exactly one result per input?
**In V1: NO (FAILED on batches != 100).**  
On batches with size $\ne 100$ (such as Builderr's 1,000-company batch), V1 crashed and returned 0 results.  
**Required V2 Fix:** Automatically process $N$ input companies (from 1 to 10,000+) and return exactly $N$ compliant terminal envelopes in identical sequence.

### 4. Are organisation numbers preserved exactly?
**In V1: PARTIAL.**  
When the input was 100 companies from the benchmark fixture, numbers were preserved; on arbitrary batches, the script aborted before writing outputs.  
**Required V2 Fix:** Strict normalization guaranteeing that every 9-digit Modulo 11 organisation number in the input has an exact 1:1 match in the output envelope stream in identical order.

### 5. Are accepted facts present in the official output envelope?
**In V1: NO (FAILED).**  
Because the script aborted or ran in snapshot mode on unknown entities, zero accepted facts reached the evaluator. Furthermore, V1 only supported 6 basic claims (`legal_name`, `legal_form`, `employees`, `municipality`, `annual_revenue`, `official_website`), omitting `registered_address`, `accounting_obligation`, `operating_result`, `people`, `locations`, `jobs`, `public_activity`, and `ratings_and_reviews`.  
**Required V2 Fix:** Complete standard 11+ claim family emission with full legal grounding for every company.

### 6. Does every accepted fact contain valid evidence?
**In V1: NO (FAILED).**  
In V1, when a company was not found, dummy claims sometimes referenced an evidence object containing dummy 64-zero SHA hashes (`"0" * 64`) or empty claim spans, triggering evaluator validation failure.  
**Required V2 Fix:** Strict cryptographic evidence integrity invariant: Every `available` claim must reference $\ge 1$ verified evidence ID with a real HTTP(S) URL, ISO-8601 UTC timestamp, non-zero SHA-256 hash, and verifiable text span.

### 7. Do source URLs and retrieval dates survive serialization?
**In V1: YES (when serialized).**  
However, because serialization failed to occur on evaluator runs, the data was never received.  
**Required V2 Fix:** Enforce Pydantic contract validation before emitting any JSONL line to disk.

### 8. Are outputs generated live rather than only from a bundled snapshot?
**In V1: NO (FAILED).**  
V1 defaulted to `--mode snapshot`. Unless `--live` was passed, it refused to make network requests.  
**Required V2 Fix:** Default to `auto` mode: Use fast local snapshot as an accelerated cache layer, but automatically execute live official Brreg and web requests for all live/unseen companies, ensuring 100% coverage on any of Norway's 411,160 companies.

### 9. Does it install from a clean clone?
**In V1: PARTIAL.**  
Dependencies in `pyproject.toml` were specified, but running required setting `PYTHONPATH=src` manually if not installed in editable mode (`pip install -e .`).  
**Required V2 Fix:** Provide clean-clone installation instructions (`pip install -e .` or automated wrapper) ensuring `python3 scripts/run_competition_batch.py` works out of the box on a vanilla Linux/macOS machine.

### 10. Does the documented one-line command actually work?
**In V1: NO (FAILED).**  
The documented command in `submission/SUBMISSION_EMAIL.txt`:  
`python3 scripts/run_competition_batch.py --organisations data/input/benchmark-100.jsonl --bulk data/input/signalpost-universe.jsonl.gz --profiles-output out/profiles.jsonl --output out/envelopes.jsonl --report out/run-report.json --run-id eval-001 --expected-count 100`  
failed because:
1. It hardcoded `data/input/benchmark-100.jsonl` rather than taking the evaluator's input file.
2. It hardcoded `--expected-count 100` which crashed on Builderr's 1,000-company batch.
3. It omitted `--live`, causing zero live lookups.  
**Required V2 Fix:** Simplify the evaluator command to:  
`python3 scripts/run_competition_batch.py --organisations <INPUT> --output <OUTPUT> --report <REPORT>`  
with all other flags having automated, robust defaults.

---

## Action Plan for V2

1. **Build Official-Contract Validator Harness (`scripts/validate_builderr_contract.py`)**: Tests arbitrary input formats, arbitrary batch sizes ($N=1, 37, 100, 1000$), live entity lookups, and strict schema compliance.
2. **Universal CLI Runner (`scripts/run_competition_batch.py`)**:
   - Default `--bulk` to bundled archive if present, but never require it.
   - Automatically determine batch size from input (remove `--expected-count` requirement).
   - Default to `auto` mode (live lookup enabled for all entities not found in snapshot).
   - Accept any input format (JSONL, JSON array, raw text list of org numbers).
3. **Comprehensive Live Fallback**: Any organisation number not in the snapshot is immediately queried live against Brreg open APIs.
