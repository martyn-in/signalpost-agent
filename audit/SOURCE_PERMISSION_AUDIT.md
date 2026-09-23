# Signalpost — Source Permission & Compliance Audit

**Audit Standard:** Builderr Signalpost Permitted Sources Policy  
**Evaluation Date:** 2026-09-23  

---

## Source Inventory & Permitted Status Table

| Source Name | Domain / Hostname | Purpose | Permitted? | Builderr Policy Reference | Default Enabled? | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Enhetsregisteret Bulk** | `data.brreg.no` | Frozen universe & company identity anchor | **YES** | Section 5: Authoritative Norwegian Registers | **YES** | Read locally from verified frozen snapshot `signalpost-universe.jsonl.gz`. |
| **Enhetsregisteret Live API** | `data.brreg.no` | Live verification of legal status, updates | **YES** | Section 5: Authoritative Norwegian Registers | **YES** (Live Mode) | Rate-limited and cached. |
| **Regnskapsregisteret API** | `data.brreg.no` | Annual accounts & financial filings | **YES** | Section 5: Authoritative Norwegian Registers | **YES** (Live Mode) | Official government accounting register. |
| **Brreg Roller API** | `data.brreg.no` | Management & board roles | **YES** | Section 5: Authoritative Norwegian Registers | **YES** (Live Mode) | Verified official management roles. |
| **Brreg Underenheter API** | `data.brreg.no` | Registered subunit locations | **YES** | Section 5: Authoritative Norwegian Registers | **YES** (Live Mode) | Official branch / subunit locations. |
| **Brreg Accounting Rules** | `www.brreg.no` | Accounting obligation rule interpretation | **YES** | Section 5: Authoritative Norwegian Registers | **YES** | Categorical rules for legal forms. |
| **Company Official Websites** | Discovered company domains | Public contact, about, news, careers | **YES** | Section 5: Company-Owned Sources | **YES** (Live Mode) | Filtered strictly by Entity Identity Gate. |
| **Brave Search API** | `api.search.brave.com` | Candidate website discovery | **YES** | Permitted Public Search / Discovery | **NO** (Optional) | Disabled by default ($0.00 base cost). Requires user key. |
| **LinkedIn Guest Scraper** | `linkedin.com` | Career / headcount exploration | **NO (Prohibited)** | Section 5: Restricted Platforms Prohibited | **NO (Disabled)** | Retained only as non-default POC script. Never invoked in default batch or evaluator. |
| **Google News RSS** | `news.google.com` | News monitoring exploration | **Permitted** | Section 5: Permitted Public News | **NO** | Available as standalone script. |

---

## Compliance Confirmation
No prohibited third-party platforms (LinkedIn, Glassdoor, Indeed, Meta) are queried in the default evaluation or competition batch pipelines. All default data originates from official Norwegian government registers and verified company-owned websites.
