# Signalpost — Refresh & Idempotency Audit Report

**Audit Target:** `src/signalpost/refresh/diff.py`, `src/norway_company_agent/refresh.py`, and `scripts/run_refresh_replay.py`  
**Audit Date:** 2026-09-23  
**Auditor:** Antigravity Autonomous Audit  

---

## 1. Idempotent Rerun Verification
- **Test:** Replaying the exact same dataset against identical source snapshots.
- **Assertion:**
  - `diff_datasets(dataset, copy.deepcopy(dataset)) == []`
- **Observed Result:**
  - **Zero Duplicate Facts Emitted**
  - **Zero False Changes Emitted**
- **Status:** **PASS**

---

## 2. Truthful Evaluation of Walkthrough "100% Precision / Recall" Claim
- **Previous Walkthrough Claim:** "100% refresh precision, 100% refresh recall".
- **Zero-Trust Audit Reality:**
  - The "100% precision/recall" metric was generated from `out/refresh-demo.json`, which was evaluated against a **synthetic micro-fixture containing exactly 1 company (`923609016`) and 2 expected change events** (employee count change from 2 to 3, and financial account restatement).
  - Claiming "100% precision / 100% recall" without qualifying the fixture size is misleading. While the diff engine performed flawlessly on that test case (2 true positives, 0 false positives, 0 false negatives), it is an engineered test fixture rather than an empirical evaluation across hundreds of live company updates.
- **Audit Recommendation:** All documentation and final reports must explicitly note the fixture size (`N=1 company, 2 change events`).

---

## 3. Real Change vs Source Failure Red-Team Scenarios

| Scenario | Input Change | Expected Behavior | Observed Behavior | Status | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Role Change** | CEO A replaced by CEO B in `/roller` | Old fact preserved in history, new fact emitted, typed `role_changed` event emitted | Emits typed change record with both old and new values and respective SHA-256 hashes | **PASS** | Verified in `test_detects_real_role_change`. |
| **Workforce Growth** | Employee count grows from 12 to 18 | `workforce_updated` event emitted with old=12, new=18 | Emitted `evt-...` with change_type `workforce_updated` | **PASS** | Verified in `test_detects_workforce_growth`. |
| **Source Timeout / Error** | Source fails with 500 / timeout | **Must NOT emit "fact removed"**; must classify as `unobserved` / `source_error` | Baseline emitted `old_val != None, new_val == None` change event | **P1 BUG FIXED** | Fixed in `refresh.py`: When a module's status is `source_error`, `failed`, or `blocked`, it is treated as unobserved and does NOT generate a business fact removal event. |
| **Address Update** | Municipality changes from Oslo to Bærum | Emits `value_updated` event with old and new municipality | Emits change with old="OSLO", new="BÆRUM" | **PASS** | Tracked in `TRACKED_FIELDS`. |
| **Financial Period Addition** | New accounting year filed (e.g. 2025) | Emits `financial_update` event with new financial record | Emits change with updated records | **PASS** | Verified in `refresh-demo.json`. |
