# Entity Resolution & Identity Verification

Signalpost enforces a strict identity matching model to completely prevent **wrong-company publications**, which are fatal under Builderr evaluation rules. A web page or domain is never accepted simply because its name resembles the target entity.

---

## 1. Identity Key Hierarchy
1. **Primary Key**: The Norwegian 9-digit Organisation Number (`organisasjonsnummer`).
2. **Authoritative Entity Anchor**: Official record in Brønnøysundregistrene (Enhetsregisteret), providing canonical legal name, legal form, registered postal address, municipality code, and registered website (if declared).
3. **Candidate Sources**: Discovered web pages, sitemaps, search candidates, and social links.

---

## 2. Match Signals & Scoring

For every candidate web page or domain, Signalpost evaluates an identity confidence score ($S \in [0.0, 1.0]$):

### Strong Positive Signals (+0.5 to +1.0)
- **Exact Organisation Number**: The 9-digit number appears formatted or unformatted within the homepage, footer, imprint, or legal terms (`score = 1.0`).
- **Registry Declared Website**: The candidate domain is explicitly registered in Brønnøysundregistrene as the company's official website (`score = 0.95`).
- **Exact Multi-Token Legal Name**: All normalized legal name tokens appear together in homepage title, headings, or structured JSON-LD (`score = 0.95`).
- **Matching Registered Address & Postal Code**: The street address and Norwegian postal code match the official registered business address.

### Moderate Positive Signals (+0.2 to +0.4)
- Distinctive single-word legal name match with substantive business content (`score = 0.90`).
- Majority token overlap ($>= 75\%$) with matching municipality and industry category.
- Stated executive/board member in official records appears on the team/leadership page.

### Negative Signals & Hard Rejection Rules
- **Conflicting Organisation Number**: Any page presenting a different 9-digit Norwegian organisation number triggers an **immediate, unconditional rejection** (`score = 0.0`).
- **Parked / For-Sale Domain**: Detected parked placeholder, domain sales banner, or generic registrar holding page (`score = 0.1`, rejected).
- **Sports Club / Association Entity Trap**: Entities registered as company sports clubs (`B.I.L.` or `Bedriftsidrettslag`) that point to the parent operating company's corporate website without club-specific evidence are quarantined (`score = 0.3`).
- **Parent / Subsidiary Confusion**: Operating company vs holding company distinction is preserved; a parent entity's facts are not attributed to a subunit unless explicitly verified.

---

## 3. Decision Status Categories

| Status | Confidence Range | Action |
| :--- | :--- | :--- |
| **`exact`** | $S \ge 0.90$ | Verified. Domain and pages are published as official company sources; facts extracted are bound to the company profile. |
| **`review`** | $0.80 \le S < 0.90$ | Probable match, but lacks conclusive proof (e.g. org number). Quarantined; not published as an official source without corroborating evidence. |
| **`related_or_uncertain`** | $S < 0.80$ | Ambiguous or unrelated. Quarantined; marked as `ambiguous` or `not_available` in output claims. |
| **`rejected`** | $S = 0.0$ | Hard rejection. Discarded immediately. |

---

## 4. Same-Name Entity Disambiguation
When multiple Norwegian companies share identical or near-identical names (e.g., "Nordic Energy AS" registered in Oslo vs "Nordic Energy AS" registered in Bergen):
- Signalpost anchors solely on the unique 9-digit organisation number.
- Address, municipality code, and registered officers are cross-referenced to ensure no cross-contamination of facts occurs between namesake entities.
