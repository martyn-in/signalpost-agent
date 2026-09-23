# Signalpost — Entity Resolution Red Team Audit Report

**Audit Date:** 2026-09-23  
**Auditor:** Antigravity Autonomous Red Team  
**Evaluation Standard:** Zero Tolerance for Material Wrong-Company Matches  

---

## 1. Adversarial Test Cases & Results

| Case ID | Scenario | Input Org & Target Legal Name | Discovered Candidate Domain & Content | Signals Detected | Score | Decision | Conformance / Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **A** | Two companies with similar name in different cities | `912345678` (Bergen Rørlegger AS) | `rørlegger-oslo.no` — "Bergen Rørlegger AS avd Oslo org 998877665" | Conflicting 9-digit org `998877665` | `0.0` | **REJECTED (quarantined)** | **PASS** — Hard rejected. |
| **B** | Same brand, different legal entities | `911111111` (Acme Retail AS) | `acme.no` — "Acme Holding AS org nr 922222222" | Conflicting 9-digit org `922222222` | `0.0` | **REJECTED (quarantined)** | **PASS** — Parent holding not attributed to operating retail subsidiary. |
| **C** | Parent and subsidiary on separate domains | `933333333` (Subco Nordic AS) | `parentcorp.com` — "Parent Corp ASA org nr 944444444" | Conflicting 9-digit org `944444444` | `0.0` | **REJECTED (quarantined)** | **PASS** — Prevents parent umbrella site from overriding subsidiary. |
| **D** | Norwegian company vs foreign namesake | `955555555` (Nordic Solutions AS) | `nordicsolutions.co.uk` — "Nordic Solutions Ltd UK. Registered in England & Wales" | Foreign legal form `Ltd`, foreign jurisdiction text, no .no TLD | `0.95` (Baseline) → **0.30** (Hardened) | **Baseline FAIL → Hardened PASS** | **VULNERABILITY IDENTIFIED & REMEDIATED**: Baseline token overlap previously passed `Nordic Solutions Ltd UK`. Hardened logic detects foreign legal suffixes (`ltd`, `inc`, `gmbh`, `llc`) and foreign registration markers to quarantine. |
| **E** | Company recently renamed | `966666666` (Fjord Tech Solutions AS) | `fjordtech.no` — "Fjord Tech Solutions AS (tidligere Fjord Maritime AS)" | Exact current legal name tokens present on homepage header | `0.95` | **EXACT (publishable)** | **PASS** — Grounded in current registered name tokens. |
| **F** | Homepage without org number | `988888888` (Viken Rådgivning AS) | `vikenradgivning.no` — "Viken Rådgivning AS - Rådgivningstjenester" | Exact legal name tokens in title/headers + Norwegian content | `0.95` | **EXACT (publishable)** | **PASS** — Allowed only when exact legal name tokens match without conflicting signals. |
| **G** | Candidate website contains DIFFERENT Norwegian org number | `977777777` (Alfa Consulting AS) | `alfaconsulting.no` — "Alfa Consulting AS org nr 988888888" | Detected conflicting 9-digit org `988888888` | `0.0` | **REJECTED (quarantined)** | **PASS** — Conflicting org number triggers immediate hard rejection. |
| **H** | Candidate website contains multiple org numbers | `915637353` (SKS Produksjon AS) | `sks.no` — Group portal listing holding `980...` and subsidiaries | Group homepage lacks subsidiary as primary entity | `0.60` | **AMBIGUOUS (not publishable)** | **PASS** — Umbrella sites listing multiple org numbers quarantined. |
| **I** | Parked / For-sale domain | `999111222` (Kreativ Design AS) | `kreativdesign.com` — "Buy this domain at HugeDomains" | Parked marker `HugeDomains` | `0.1` | **REJECTED (quarantined)** | **PASS** — Parked domain markers catch registrar placeholders. |
| **J** | Inactive website / server error | `922333444` (Tom Butikk AS) | `tombutikk.no` — HTTP 404 / 500 error | Connection failure / empty response | `0.0` | **FAILED / NOT_AVAILABLE** | **PASS** — Labeled `failed` or `not_available`, never guessed. |
| **K** | Shared corporate website for multiple subsidiaries | `915637353` (SKS Produksjon AS) | `sks.no` — SKS power group | Subsidiary name only in sub-page text | `0.60` | **AMBIGUOUS (not publishable)** | **PASS** — Quarantined under `WebsiteIdentityTests.test_group_contact_page`. |

---

## 2. Hardening Strategy Implemented
1. **Conflicting Org Number Hard Gate:** Any candidate page displaying a valid 9-digit Norwegian organisation number that does NOT match the target company's organisation number is assigned Score `0.0` and `status: rejected`.
2. **Foreign Jurisdiction Quarantine:** If no 9-digit Norwegian organisation number is found on the page, the presence of foreign corporate designations (`ltd`, `llc`, `gmbh`, `sarl`, `inc`, `corp`, `plc`, `oy`, `ab`) or foreign jurisdiction phrasing (`registered in england`, `delaware`, `companies house`) immediately disqualifies the page from `exact` status and downgrades it to `review` / `related_or_uncertain` (`publishable: False`).
3. **Parked Marker Protection:** Expanded list of registrar, parking, and for-sale patterns ensures zero parking pages leak into published company profiles.
