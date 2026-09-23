# Security Hardening & SSRF Mitigation Policy

Signalpost handles untrusted URLs discovered from registry filings, search APIs, and crawled web pages. Rigorous security boundaries are enforced to prevent Server-Side Request Forgery (SSRF), secret leakage, and denial-of-service vulnerabilities.

---

## 1. Safe URL Validation & SSRF Prevention

All outbound URLs pass through `assert_public_url()` before any socket connection is opened or DNS resolution occurs:

### Forbidden Schemes
- Allowed schemes: strictly `http://` and `https://`.
- Blocked schemes: `file://`, `ftp://`, `gopher://`, `data:`, `javascript:`, `dict:`, `ldap:`, `ssh:`.

### Forbidden Network Targets & IP Ranges
1. **Loopback**: `127.0.0.0/8`, `::1`, `localhost`, `0.0.0.0`.
2. **Private IPv4 Subnets (RFC 1918)**:
   - `10.0.0.0/8`
   - `172.16.0.0/12`
   - `192.168.0.0/16`
3. **Link-Local & Cloud Metadata Endpoints**:
   - `169.254.0.0/16` (including AWS/GCP/Azure instance metadata endpoint `169.254.169.254`).
   - `fe80::/10` (IPv6 link-local).
4. **Broadcast & Multicast**:
   - `224.0.0.0/4`
   - `255.255.255.255`
5. **Reserved / Internal Hostnames**:
   - `*.local`, `*.internal`, `*.lan`, `*.corp`, `*.test`.
6. **Embedded Credentials**:
   - URLs containing `user:password@host` are rejected to prevent credential injection or leakage.

### Redirect Chain Validation
- Every redirect hop is independently validated against the SSRF filter before following. If an initially public URL attempts to redirect to `http://169.254.169.254/latest/meta-data/` or `http://127.0.0.1:8080/`, the redirect is blocked immediately.

---

## 2. Resource & Denial-of-Service Defenses
- **Response Size Cap**: Maximum response body size is capped at 5 MB for HTML and 15 MB for annual account PDF filings. Streams exceeding this limit are aborted.
- **Connection & Read Timeouts**:
  - Connect timeout: 5.0 seconds.
  - Read timeout: 10.0 seconds.
  - Total per-request timeout: 15.0 seconds.
- **Recursion & Crawl Depth Limits**: Maximum subpage crawl depth is limited to 1 (direct links from homepage only), avoiding spider traps, infinite calendar loops, and faceted search explosions.

---

## 3. Secret & Credential Handling
- Zero credentials or tokens are hardcoded in the codebase.
- Optional API keys (`SEARCH_API_KEY`, `LLM_API_KEY`) are read strictly from environment variables.
- Structured logging redacts authorization headers, API keys, and sensitive environment parameters.
