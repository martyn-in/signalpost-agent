# Builderr Signalpost Output Contract Comparison

**Standard:** `OUTPUT_CONTRACT.md` (Scoring V2, Builderr Official)  
**Evaluated Artifact:** `submission/envelopes.jsonl` (and `src/signalpost/result_contract.py`)  
**Audit Date:** 2026-09-23  

---

## Field-by-Field Conformance Table

| JSON Path | Builderr Specification | Signalpost Implementation | Exact Match? | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `organisation_number` | String, 9 Norwegian digits | String, 9 digits (`str(profile['organisation_number'])`) | **YES** | Strict Modulo 11 check verified. |
| `run` | Object containing run metadata | Object containing run metadata | **YES** | Dict structure verified. |
| `run.run_id` | String identifying the execution batch | String (`args.run_id` or `submission-run-v1`) | **YES** | Uniquely tracks the run. |
| `run.started_at` | ISO-8601 UTC timestamp string | ISO-8601 string (`YYYY-MM-DDTHH:MM:SS.fZ`) | **YES** | Conforms to UTC format. |
| `run.completed_at` | ISO-8601 UTC timestamp string | ISO-8601 string (`YYYY-MM-DDTHH:MM:SS.fZ`) | **YES** | Conforms to UTC format. |
| `run.terminal_status` | Status string (e.g. `completed`) | String: `"completed"` | **YES** | Indicates terminal outcome. |
| `claims` | Array of claim objects | Array of claim objects | **YES** | Contains individual asserted claims. |
| `claims[].field` | String: name of attribute (`legal_name`, `annual_revenue`, etc.) | String matching known entity fields | **YES** | Standardized domain field names. |
| `claims[].value` | Any primitive or object; null when unavailable | Preserves raw type or `None` | **YES** | Missing values never converted to 0. |
| `claims[].availability` | Enum: `available`, `not_available`, `blocked`, `not_applicable`, `ambiguous`, `failed` | Strict set of 6 enums | **YES** | Validated against `VALID_AVAILABILITIES`. |
| `claims[].confidence` | Float between 0.0 and 1.0 | Float between 0.5 and 1.0 | **YES** | 1.0 for registry; 0.95 for verified web. |
| `claims[].evidence_ids` | Array of string IDs pointing into `evidence` | Array of string IDs `["ev-{org}-{idx}"]` | **YES** | Empty list for unobserved/unavailable. |
| `evidence` | Array of evidence provenance objects | Array of evidence provenance objects | **YES** | Captures source proof. |
| `evidence[].id` | Unique string ID matching reference in claims | String `f"ev-{org_number}-{counter}"` | **YES** | Referenced by `claim.evidence_ids`. |
| `evidence[].source_url` | Valid URL string (http/https) | String URL (`https://data.brreg.no/...`) | **YES** | SSRF-validated public URL. |
| `evidence[].source_class` | Source class string (e.g. `official_registry`, `company_owned`) | String enum (`official_registry`, `company_owned`, etc.) | **YES** | Categorizes source authority. |
| `evidence[].retrieved_at` | ISO-8601 UTC timestamp string | ISO-8601 UTC timestamp string | **YES** | Valid timestamp. |
| `evidence[].content_sha256` | 64-character hexadecimal SHA-256 string | 64-character SHA-256 hash | **YES** | Content-addressed cryptographic hash. |
| `evidence[].claim_span` | Text excerpt or locator string | Text excerpt verifying the claim | **YES** | Verifiable text span. |
| `changes` | Array of change records for refresh | Array of change objects | **YES** | Empty on initial run, populated on refresh. |
| `errors` | Array of error descriptions | Array of error strings | **YES** | Populated if partial failures occur. |
| `operations` | Object tracking resource consumption | Object tracking resource consumption | **YES** | Conforms to budget reporting. |
| `operations.requests` | Integer count of outbound requests | Integer (`0` in snapshot mode) | **YES** | Counts redirects and retries. |
| `operations.runtime_ms` | Integer runtime in milliseconds | Integer elapsed time in milliseconds | **YES** | Measured per company. |
| `operations.third_party_cost_usd` | Float cost in USD | Float (`0.0` for default open pipeline) | **YES** | Explicitly declared. |

---

## Schema Conformance Summary
- `submission/envelopes.jsonl`: **1,000 / 1,000 Envelopes Conforming (0 errors)**.
- `scripts/run_competition_batch.py`: **P0 Discrepancy Found & Fixed** — Previously called `norway_company_agent.batch.terminal_envelope` instead of `signalpost.result_contract.build_output_envelope`.
