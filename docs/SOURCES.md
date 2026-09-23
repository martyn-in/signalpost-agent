# Permitted Sources Registry & Licensing Policy

Signalpost strictly follows the Builderr Permitted Sources Policy (`starter-briefs/signalpost-sources.md`). Only lawful, public, auditable sources are utilized.

---

## 1. Source Registry Table

| Source | Category | Base Domain / Endpoint | Access Method | Auth Required | Ext. Cost | Rate Limits / Policy | Supported Fact Types |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Brønnøysundregistrene Enhetsregisteret** | Official Registry | `data.brreg.no/enhetsregisteret/api/enheter/` | REST JSON / Bulk CSV | None | $0 | Standard public API polite rate limits | Legal name, org number, legal form, address, municipality, industry NACE, employee count, status |
| **Brønnøysundregistrene Regnskapsregisteret** | Official Financials | `data.brreg.no/regnskapsregisteret/regnskap/` | REST JSON | None | $0 | Standard public API polite rate limits | Annual filed revenue, operating profit, profit before tax, annual result, assets, equity, debt, reporting period |
| **Brønnøysundregistrene Roller** | Official Roles | `data.brreg.no/enhetsregisteret/api/enheter/{org}/roller` | REST JSON | None | $0 | Standard public API polite rate limits | Management (daglig leder), board of directors (styreleder, styremedlemmer), auditor, accountant |
| **Brønnøysundregistrene Underenheter** | Official Subunits | `data.brreg.no/enhetsregisteret/api/underenheter` | REST JSON | None | $0 | Standard public API polite rate limits | Operational locations, branch addresses, subunit employee counts, subunit NACE |
| **Brønnøysundregistrene Årsregnskap Kopi** | Official Filings | `data.brreg.no/regnskapsregisteret/regnskap/aarsregnskap/kopi/` | REST JSON / PDF | None | $0 | Reserved slot: >= 2.1s delay between request starts (max 30 req/min) | Available filing years, direct PDF download links for statutory accounts |
| **Verified Official Website** | Company Owned | Company root domain | Async HTTP GET (robots-checked) | None | $0 | Max 2–4 req/domain, backoff on 429/503 | Company description, products, services, contact email, phone, social profile links, headquarters |
| **Official Subpages** | Company Owned | `/om-oss`, `/kontakt`, `/ledelse`, `/karriere`, `/aktuelt` | Async HTTP GET | None | $0 | Max 2–4 req/domain, max 3–5 subpages/company | Extended description, team members, office addresses, job openings, news releases |
| **Embedded Structured Data** | Company Owned | Schema.org JSON-LD, Microdata, OpenGraph | Extracted from HTML | None | $0 | Extracted inline from crawled HTML | Organization names, addresses, logos, founders, social profiles |
| **Public Jobs Feeds / Pages** | Permitted Careers | Company careers page / Nav Arbeidsplassen Open API | REST JSON / HTML | None | $0 | Standard polite crawling | Open job positions, job titles, department, location, posted date |

---

## 2. Platform Access Restrictions & Compliance

### Restricted Platforms Policy
- **LinkedIn, Meta (Facebook/Instagram), Indeed, Glassdoor**: Direct automated scraping or reverse-engineered private APIs without formal developer credentials is strictly prohibited by platform terms of service.
- **Handling in Signalpost**:
  - Social media URLs discovered on verified company websites are parsed and corroborated using lexical handle matching.
  - If a platform is not lawfully accessible via a permitted public API, Signalpost records the status honestly as `not_available` or `blocked`, rather than deploying brittle or unauthorized scrapers.

### Rate Limiting & Politeness
- All web crawls adhere to `robots.txt` specifications.
- Domain concurrency is capped to 2 concurrent connections per host.
- Polite request delays (minimum 500ms between requests to the same domain) prevent unintentional server overload.
- Brønnøysund history copies enforce a deterministic 2.1-second token bucket delay to comply with the 30 requests/minute API ceiling.
