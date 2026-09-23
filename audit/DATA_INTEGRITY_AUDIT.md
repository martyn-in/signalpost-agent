# Signalpost — Data Provenance & Integrity Audit

**Audit Target:** `submission/profiles.jsonl`, `submission/envelopes.jsonl`, `submission/organisation_numbers.txt`  
**Audit Date:** 2026-09-23  

---

## 1. Test Fixture & Mock Data Leakage Search
- **Search Query:** `\b(example|dummy|mock|fixture|fake|sample|placeholder|lorem)\b` across all 1,000 submission profiles and envelopes.
- **Observed Matches in Submission Artifacts:** **0**
- **Conclusion:** No synthetic or mock data from tests leaked into the 1,000 submission profiles or envelopes.

---

## 2. Demographic & Distribution Checks Across 1,000 Companies
- **Unique Companies:** Exactly 1,000 unique Norwegian legal entities.
- **Unique Legal Names:** Exactly 1,000 distinct names (0 duplicate names).
- **Legal Form Distribution:**
  - `AS` (Aksjeselskap): 926 (92.6%)
  - `BRL` (Borettslag): 18
  - `STI` (Stiftelse): 14
  - `ESEK` (Eierseksjonssameie): 12
  - `NUF` (Norsk avdeling av utenlandsk foretak): 8
  - `FLI` (Forening/lag/innretning): 7
  - `SA` (Samvirkeforetak): 3
  - `DA` (Delt ansvar): 3
  - `VPFO` (Verdipapirfond): 3
  - `ANS` (Ansvarlig selskap): 2
  - `ENK` (Enkeltpersonforetak): 2
  - `SPA` (Sparebank): 1
  - `PK` (Pensjonskasse): 1
- **Geographic Distribution:**
  - 197 distinct municipalities across Norway.
  - Top 5: Oslo (204), Bergen (57), Bærum (39), Trondheim (35), Stavanger (24).
- **Industry Classification:**
  - 206 distinct 5-digit NACE industry codes.
- **Workforce / Employees:**
  - 144 companies report registered employees.
  - Headcount ranges from 5 to 2,441 (average 43.2).
  - 856 companies have `null` registered employees (common for holding, investment, and property entities).
- **Websites:**
  - 107 companies have officially registered websites in their Brreg record.

---

## 3. Structural Claim Pattern Audit
- In the initial baseline `submission/envelopes.jsonl`, each company envelope contained exactly 5 claim slots:
  `legal_name`, `legal_form`, `employees`, `annual_revenue`, `official_website`.
- For `annual_revenue`, since the snapshot dataset contained `accounting_obligation` rather than full line-item P&L statements for these companies, revenue was set to `None` with status `not_available` (or `not_applicable` for ENK/FLI).
- For `official_website`, the baseline logic previously failed to promote registry-declared websites to `available`, marking them `not_available`. This is addressed in the P1 pipeline remediation.
