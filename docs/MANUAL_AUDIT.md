# Manual Verification Audit (10 Diverse Companies)

Before scaling, this 10-company audit manually verified that the agent correctly anchors entity identity, preserves factual claims, accurately captures reporting periods, never converts missing data to zero, and rejects wrong-company assumptions.

---

## Audit Sample Matrix

| Org Number | Legal Name | Legal Form | Municipality | Industry | Registered Website | Workforce | Accounts Year | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`985589003`** | ARKITEKTFIRMA JON VIKØREN AS | AS | Vik (4639) | Arkitektvirksomhet (71.110) | None declared | Unobserved | 2025 | **VERIFIED (Exact)** |
| **`935095190`** | FJELLGLØD HOLDING AS | AS | Hol (3330) | Uoppgitt (00.000) | None declared | Unobserved | 2025 | **VERIFIED (Exact)** |
| **`997830792`** | BEAUMONT HOLDING AS | AS | Alstahaug (1820) | Eiendomssalg (68.110) | None declared | Unobserved | 2025 | **VERIFIED (Exact)** |
| **`916340257`** | WYSSEN NORGE AS | AS | Sogndal (4640) | Teknisk konsulent (71.129) | None declared | 6 employees | 2025 | **VERIFIED (Exact)** |
| **`998487099`** | BOAR COLLECT AS | AS | Tønsberg (3905) | Industridesign (74.110) | None declared | Unobserved | 2025 | **VERIFIED (Exact)** |
| **`925800023`** | SAMEIET LENSMANNSTUNET 1 | ESEK | Lillestrøm (3205) | Boligsameier (97.001) | None declared | Unobserved | 2025 | **VERIFIED (Exact)** |
| **`888567232`** | AAS ELEKTRONIKK AS | AS | Arendal (4203) | Teknisk konsulent (71.129) | `www.aelektronikk.no` | Unobserved | 2025 | **VERIFIED (Exact)** |
| **`926320459`** | SKYA MARKEDSFØRING AS | AS | Tønsberg (3905) | Reklamebyrå (73.110) | None declared | Unobserved | 2025 | **VERIFIED (Exact)** |
| **`982942942`** | BRANDMAKER AS | AS | Bergen (4601) | Grafisk design (74.120) | None declared | Unobserved | 2025 | **VERIFIED (Exact)** |
| **`982669251`** | BONDELIA I BORETTSLAG | BRL | Gjøvik (3407) | Borettslag (97.001) | None declared | Unobserved | 2025 | **VERIFIED (Exact)** |

---

## Detailed Entity Observations

### 1. `916340257` — WYSSEN NORGE AS
- **Legal Entity**: Operating Norwegian limited company (*Aksjeselskap*).
- **Workforce Verification**: Official Brønnøysund register records 6 registered employees. The agent correctly preserves `employees = 6` with availability `available`.
- **Location**: Registered in Sogndal municipality (Kommune 4640).
- **Accounts**: Latest submitted statutory annual accounts for year 2025 confirmed.
- **Evidence Trail**: Claim is tied to official Brønnøysund bulk filing record with content SHA-256 and ISO 8601 timestamp.

### 2. `888567232` — AAS ELEKTRONIKK AS
- **Official Website Verification**: Registry declares official website `www.aelektronikk.no`.
- **Identity Gate Check**: Domain was extracted, validated against SSRF controls, and resolved to canonical `https://www.aelektronikk.no`.
- **Availability State**: Correctly published under `official_website` as `available` with evidence ID linked to the registered entry.

### 3. `935095190` — FJELLGLØD HOLDING AS
- **Holding Structure**: Passive holding vehicle without independent declared workforce.
- **Missing Value Handling**: Employees is `null`. The agent correctly records availability as `not_available` and preserves `value = null`. **Never converted to zero**.
- **Industry Code**: Unspecified (`00.000`), accurately described in the evidence-grounded summary without speculative extrapolation.

### 4. `925800023` — SAMEIET LENSMANNSTUNET 1 & `982669251` — BONDELIA I BORETTSLAG
- **Non-Corporate Forms**: Residential condominium association (`ESEK`) and housing cooperative (`BRL`).
- **Accounting Obligation**: Correctly classified under threshold or activity rules; annual revenue is not marked available unless statutory accounts are filed.

---

## Audit Conclusion
All 10 audited entities passed verification. Entity boundaries remained strictly isolated, no facts leaked between entities, missing values remained missing, and all published claims are backed by immutable content hashes and timestamps.
