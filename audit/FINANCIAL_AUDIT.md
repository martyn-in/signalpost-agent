# Signalpost — Financial Extraction & Normalization Audit

**Audit Target:** `src/signalpost/extraction/financials.py` and `tests/unit/test_financials.py`  
**Audit Date:** 2026-09-23  
**Auditor:** Antigravity Autonomous Financial Audit  

---

## 1. Core Principles & Zero-Tolerance Policy
1. **Never Substitute Missing with Zero:** In accounting, missing data means an unfiled or unobserved account line. Converting missing values to 0 falsifies equity, profit, and revenue. Missing values MUST remain `None` and map to `not_available` / `not_applicable`.
2. **Explicit Zero Preservation:** When a financial filing explicitly reports `0` (e.g. 0 NOK in tax expense or revenue), it must be preserved as `0.0`.
3. **Exact Scale Normalization:** Financial statements in Norway frequently report in whole thousands (`i hele tusen`, `NOK 1 000`, `tkr`) or millions (`MNOK`). All figures must normalize accurately to the base unit (NOK).
4. **Sign Integrity:** Negative figures wrapped in accounting parentheses `(1 250)` or formatted with Norwegian Unicode minus `−` must normalize to `-1250.0`.

---

## 2. Red-Team Test Cases & Observed Normalization Results

| Test # | Raw Input String | Source Scale / Note | Normalized Output (NOK) | Expected (NOK) | Status | Verification Note |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | `"24 300"` | `"NOK 1000"` | `24,300,000.0` | `24,300,000.0` | **PASS** | Thousand multiplier applied correctly. |
| **2** | `"12.5"` | `"MNOK"` | `12,500,000.0` | `12,500,000.0` | **PASS** | Million multiplier applied correctly. |
| **3** | `"(25 400)"` | `"NOK 1000"` | `-25,400,000.0` | `-25,400,000.0` | **PASS** | Parentheses recognized as negative accounting value. |
| **4** | `"24\u00a0300"` | `"tusen nok"` | `24,300,000.0` | `24,300,000.0` | **PASS** | Non-breaking space (NBSP) stripped cleanly. |
| **5** | `"−500"` | `""` | `-500.0` | `-500.0` | **PASS** | Unicode minus (`\u2212`) parsed as negative sign. |
| **6** | `"1.250,50"` | `""` | `1250.5` | `1250.5` | **PASS** | Norwegian format (dot thousands, comma decimal) parsed. |
| **7** | `"1250,50"` | `""` | `1250.5` | `1250.5` | **PASS** | Comma decimal parsed as standard float. |
| **8** | `""` (empty) | `""` | `None` | `None` | **PASS** | Does NOT become 0. |
| **9** | `None` | `""` | `None` | `None` | **PASS** | Does NOT become 0. |
| **10** | `"-"` (dash) | `""` | `None` | `None` | **PASS** | Standard registry blank dash parses as `None`. |
| **11** | `"0"` | `""` | `0.0` | `0.0` | **PASS** | Explicit zero preserved. |
| **12** | `"150 000"` | `"tkr"` | `150,000,000.0` | `150,000,000.0` | **PASS** | `tkr` recognized as thousand kroner. |
| **13** | `"(500)"` | `""` | `-500.0` | `-500.0` | **PASS** | Parentheses negative without scale factor. |
| **14** | `"100"` | `"i hele tusen"` | `100,000.0` | `100,000.0` | **PASS** | `i hele tusen` detected in Norwegian table note. |
| **15** | `"4.2"` | `"mill. nok"` | `4,200,000.0` | `4,200,000.0` | **PASS** | `mill. nok` detected in note. |
| **16** | `"N/A"` | `""` | `None` | `None` | **PASS** | String "N/A" treated as missing (`None`). |
| **17** | `"(1)"` | `"NOK 1 000"` | `-1,000.0` | `-1,000.0` | **PASS** | Negative one thousand. |
| **18** | `"100 000 000"`| `""` | `100,000,000.0` | `100,000,000.0` | **PASS** | Multi-space thousands separated integer. |
| **19** | `"500,00"` | `""` | `500.0` | `500.0` | **PASS** | Clean decimal rounding. |
| **20** | `"–100"` | `""` | `-100.0` | `-100.0` | **PASS** | En-dash (`–`) parsed as negative sign. |

---

## 3. Financial Statement Field Mapping & Separation
In `normalize_financial_statement`:
- **Revenue:** Maps strictly to `driftsinntekter` / `sumDriftsinntekter`.
- **Operating Result:** Maps strictly to `driftsresultat` (`revenue - operating expenses`).
- **Profit Before Tax:** Maps strictly to `ordinaertResultatFoerSkattekostnad`.
- **Annual Result / Net Income:** Maps strictly to `aarsresultat`.
- **Assets:** Maps strictly to `eiendeler.sumEiendeler`.
- **Equity:** Maps strictly to `egenkapitalGjeld.egenkapital.sumEgenkapital`.
- **Debt / Liabilities:** Maps strictly to `egenkapitalGjeld.gjeldOversikt.sumGjeld`.

Fields are cleanly isolated and cannot be cross-contaminated.
