# Builderr Signalpost — Official Competition Rules & Constraints

**Official Challenge URL:** [https://builderr.ai/challenges/signalpost](https://builderr.ai/challenges/signalpost)  
**Evaluation Contract:** [https://builderr.ai/docs/signalpost-evaluation-harness.md](https://builderr.ai/docs/signalpost-evaluation-harness.md)  
**Permitted Sources:** [https://builderr.ai/starter-briefs/signalpost-sources.md](https://builderr.ai/starter-briefs/signalpost-sources.md)  
**Status:** Scoring Version 2, Effective August 26, 2026 for all Round 1 entrants.  
**Verified on:** 2026-09-23 (Full Zero-Trust Independent Audit)

---

## 1. Challenge Overview
Signalpost challenges builders to construct an autonomous research agent that receives a Norwegian organisation number, discovers facts from permitted public and authoritative sources, strictly verifies entity attribution, preserves claim-level evidence, detects updates, and produces standardized evaluator output envelopes.

**Core Philosophy:**
- **Exact Company Identity > Coverage**: A material wrong-company publication prevents official qualification.
- **Evidence Required for Every Claim**: No factual claim may be published without provenance (URL, timestamp, content hash, text span/locator).
- **Idempotent Refresh**: Rerunning against unchanged sources must create 0 duplicate facts and 0 false changes.
- **Honest Missing Data**: Missing values must NEVER silently become zero or default values.

---

## 2. Resource & Evaluation Constraints

| Constraint | Limit / Requirement |
| :--- | :--- |
| **Input Format** | Norwegian organisation numbers (9 digits) |
| **Evaluation Batch** | Exactly 100 randomly selected companies daily |
| **Runtime Limit** | Maximum 45 minutes wall-clock per 100-company run |
| **Request Limit** | Maximum 2,000 outbound HTTP requests total (redirects and retries count; cache hits are free) |
| **External API Cost** | Maximum $10 declared third-party API spend per 100-company run |
| **Hardware Environment** | ~8 vCPU, 16 GB RAM, 10 GB temporary disk |
| **Minimum Submission** | At least 1,000 completed company profiles + exact organisation-number manifest |
| **Terminal Output** | Exactly 100 terminal result envelopes for a 100-company batch |
| **Result States** | `available`, `not_available`, `blocked`, `not_applicable`, `ambiguous`, `failed` |
| **Dependency Pinning** | Pinned dependencies and one reproducible evaluator command |

---

## 3. Scoring Breakdown (100 Points Total)

1. **Coverage & Source Discovery (35 Points)**
   - For each field family: 70% company recall + 30% individual claim recall against the union of verified findings.
2. **Accuracy, Exact Identity & Evidence (30 Points)**
   - Fact belongs to the exact legal entity.
   - Complete claim provenance (source URL, retrieval timestamp, reporting period where applicable).
   - Zero tolerance for fabricated financial numbers or material wrong-company matches.
3. **Refresh & Extensibility (20 Points)**
   - Idempotent rerun: identical source snapshot yields zero duplicate facts, zero false changes.
   - Detects true changes (leadership, financials, addresses, jobs) while preserving historical evidence.
   - Source errors (e.g., 404, 500, timeout) are recorded as unobserved, NOT genuine business removals.
4. **Decision-Useful Synthesis (10 Points)**
   - Evidence-grounded briefing: company overview, operational activities, leadership, latest filed financials, open roles, dated activity, and explicit unknowns.
5. **UX & Verification Interaction (5 Points)**
   - User-friendly inspection interface on desktop and mobile allowing verification of claims and evidence citations.

---

## 4. Qualification Gates
To qualify for official ranking and awards, an entry must achieve:
- **Overall Score >= 65/100** on an official run.
- **>= 1,000 Completed Profiles** matching the submitted organisation-number manifest.
- **Exactly 100 Terminal Envelopes** for each 100-company daily evaluation batch.
- **Zero Material Wrong-Company Publications**.
- **Zero Fabricated Financial Numbers**.
- **100% Evidence Completeness** for all published claims.
- **Idempotent Refresh Verification**.

---

## 5. Permitted Sources Policy
- **Authoritative Norwegian Registers**: Brønnøysundregistrene (Enhetsregisteret bulk data & API, Regnskapsregisteret financial accounts & copies, Roller management & board, Underenheter registered subunits).
- **Company-Owned Sources**: Verified official company website, sitemaps, `/about`, `/om-oss`, `/contact`, `/ledelse`, `/locations`, `/careers`, `/news`, and embedded structured data (JSON-LD, microdata, OpenGraph).
- **Permitted Public Careers/News Sources**: Public job boards with compliant access policies, official platform APIs.
- **Strictly Prohibited**: Scraping restricted platforms (LinkedIn, Meta, Glassdoor, Indeed) without official API or licensed access; bypassing CAPTCHAs or paywalls; accessing evaluator internals.

---

## 6. Audit Mismatch Flags & Clarifications
During the zero-trust audit conducted on 2026-09-23, the following nuances and discrepancies between naive assumptions and the official Builderr specification were identified:

1. **Claim Count Semantics**:
   - Builderr specifies that emitted claims in the envelope represent individual factual assertions (`legal_name`, `legal_form`, `employees`, `annual_revenue`, `operating_result`, `official_website`, `people`, `locations`, `jobs`).
   - If a source was inspected and found to have no data (e.g. no filed accounts or no open jobs), this must be reported as `not_available` or `not_applicable`, distinct from a source that failed or was blocked.
   - Any claim marked `available` MUST have an associated evidence object with a valid `source_url`, `retrieved_at`, and `content_sha256`.

2. **Sandbox Network Egress**:
   - In environments where live external egress is sandboxed or blocked (e.g., standard runner without public internet), the evaluator operates against local snapshot mirrors (`signalpost-universe.jsonl.gz`). In this mode, outbound requests are exactly 0, runtime is dominated by local JSON/gzip parsing, and cost is $0.00.
   - Live crawling mode is fully implemented for authorized environments with uninhibited internet egress, subject to the 2,000 HTTP request hard cap.

3. **Status Enums**:
   - Allowed availability states are strictly: `available`, `not_available`, `blocked`, `not_applicable`, `ambiguous`, and `failed`. Ad-hoc status strings are strictly forbidden.
