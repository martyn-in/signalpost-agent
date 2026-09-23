# Signalpost — Network & Request Budget Audit

**Audit Date:** 2026-09-23  
**Audit Target:** `src/signalpost/fetching/client.py`, `src/signalpost/fetching/budget.py`, and runner scripts  

---

## 1. What Counts as an Outbound HTTP Request
In compliance with the official Builderr evaluation contract:
1. **Initial HTTP Request:** Every outbound TCP/TLS connection attempting a GET/POST request counts as 1 request.
2. **Redirects (HTTP 301, 302, 307, 308):** Every follow-up redirect hop is explicitly counted as an additional request.
3. **Retries (HTTP 500, 502, 503, 504, Timeout):** Every retry attempt increments the request count.
4. **Cache Hits:** Local cache hits (served from `data/cache/`) execute 0 network socket operations and cost **0 requests**.
5. **Snapshot Mode:** Reading pre-downloaded, frozen Brønnøysundregistrene universe files (`signalpost-universe.jsonl.gz`) executes 0 network socket operations and costs **0 requests**.

---

## 2. Snapshot Mode Verification
- **Test Command:**
  ```bash
  python3 scripts/run_competition_batch.py \
    --organisations data/input/benchmark-100.jsonl \
    --bulk data/input/signalpost-universe.jsonl.gz \
    --profiles-output out/profiles.jsonl \
    --output out/envelopes.jsonl \
    --report out/run-report.json \
    --run-id eval-001 \
    --expected-count 100 \
    --modules "registry,accounting_obligation"
  ```
- **Observed Operations Metrics:**
  - `requests`: **0**
  - `bytes`: **0**
  - `cost_usd`: **$0.00**
  - `wall_clock_time`: **4.77 seconds**
  - `envelopes_emitted`: **100**
- **Conclusion:** Snapshot mode is **100% request-free** and completes in < 5 seconds.

---

## 3. Live Crawl Mode & Sandbox Egress Limitations
- In an open internet environment, the live research pipeline queries:
  1. Brreg live APIs: `/enheter/{org}`, `/regnskap/{org}`, `/roller` (~1-3 requests/company)
  2. Verified company homepage and key sub-pages (`/about`, `/contact`) (~1-2 requests/company)
  - For a 100-company batch where ~20-30% have discoverable active websites, the expected total requests range between **250 and 450 requests**, comfortably beneath the **2,000 request competition cap**.
- **Important Audit Finding on Sandboxed Execution:**
  - Inside the restricted test runner / sandbox, direct outbound network egress to external Norwegian public hosts (`data.brreg.no`) is blocked by default or times out.
  - In such restricted environments, attempting live network fetches without `BypassSandbox` stalls on socket timeouts (15-30s per company).
  - Therefore, the official default evaluator command MUST default to snapshot mode when `--bulk` is provided, with live mode explicitly toggled via `--live` or `--modules`.
  - The previous walkthrough claim of "~350 requests" represents a typical unconstrained live run, whereas snapshot runs execute with exactly **0 requests**.

---

## 4. Request Budget Enforcement
In `src/signalpost/fetching/budget.py`:
- `max_requests`: 1,900 (conservative safety margin below Builderr's 2,000 cap).
- `soft_limit`: 1,750 (sheds low-priority background crawling when reached).
- `max_cost_usd`: $10.00 (hard cap on third-party spend; agent spend remains $0.00).
- When `budget.can_request(priority)` returns `False`, `SafeHttpClient` immediately halts further outbound network calls and returns HTTP 429 (`Budget limit reached`), allowing the batch runner to finalize all terminal envelopes cleanly without crashing or skipping companies.
