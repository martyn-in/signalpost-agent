# Third-Party API Cost & Resource Consumption Report

Signalpost is engineered to operate with **$0.00 declared external API cost** for standard evaluation runs, comfortably complying with the Builderr competition's **$10.00 per 100-company run** ceiling.

---

## 1. Itemized Cost Breakdown (Default Evaluator Run)

| Service / Provider | Purpose | Requests / 100 Companies | Cost per Request | Total Cost per 100 Companies |
| :--- | :--- | :--- | :--- | :--- |
| **Brønnøysundregistrene (Enhetsregisteret)** | Official Entity & Subunits | Frozen bulk / Free REST API | $0.00 | **$0.00** |
| **Brønnøysundregistrene (Regnskapsregisteret)** | Statutory Annual Accounts | Free Public REST API | $0.00 | **$0.00** |
| **Company Websites (Direct HTTP)** | Direct Web Crawl & Scraping | Direct HTTP GET (0–500 reqs) | $0.00 | **$0.00** |
| **Local Response Cache (SHA-256)** | On-Disk Replay & Caching | Free local disk I/O | $0.00 | **$0.00** |
| **Deterministic Synthesis Engine** | Profile Briefing Generator | Deterministic CPU template | $0.00 | **$0.00** |
| **Total Standard Run Cost** | - | - | - | **$0.00** |

---

## 2. Optional Configured External Tiers

If configured with third-party external services via environment variables, costs remain tightly budgeted:

| Tier / Feature | Provider | Env Variable | Cost per 100 Companies | Safety Cap |
| :--- | :--- | :--- | :--- | :--- |
| **Brave Web Search API** | Candidate Domain Discovery | `SEARCH_API_KEY` | ~$0.30–$0.50 (100–150 queries @ $3/1k) | $2.00 hard stop |
| **OpenAI / Gemini LLM** | Extended Context Extraction | `LLM_API_KEY` | ~$0.20–$0.40 (gpt-4o-mini / gemini-flash) | $3.00 hard stop |
| **Total Configured Run Cost** | - | - | **~$0.50–$0.90** | **$10.00 Max Cap** |

---

## 3. Resource Accounting Verification
During the official 100-company benchmark run:
- **Observed Third-Party API Spend:** `$0.00`
- **Competition Cost Cap:** `$10.00`
- **Cost Margin:** 100% under budget ($10.00 remaining)
- **Outbound HTTP Requests:** 0 (frozen registry snapshot mode) to ~350 (live web crawling mode), well below the 2,000 request limit.
