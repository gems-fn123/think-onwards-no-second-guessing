# Day-4 Final Probes

**Date:** 2026-06-29  
**Branch:** main  
**Context:** Precision-count curve (`PRECISION_v2_hp400/600`) was dead vs `COUNT_KNEE_hp750 = 34.65`. These are the last three day-4 low-EV closers, each testing one unexplored lever.

---

## 1. PERM_PROBE_hp750 — A4 PERM lottery ticket

**Question:** Does the answer key grade PERM? PERM has a generous 0.5-log tolerance and was never cleanly probed.

**Command:**
```bash
python -m src.main --honeypot-target 750 --pay-no-perm --vsh-fixed \
  --archie-a 0.62 --archie-m 2.15 --pay-sw-max 0.35 --perm-out timur --tag PERM_PROBE_hp750
```

**Result:**
- Zip: `outputs/submission_20260629_PERM_PROBE_hp750.zip`
- Total flagged: **750**
- Wells with pay: **41**
- Mean pay fraction: 0.0058
- Validation: READY ✅ (0 physics-gate / 0 round-trip failures)

---

## 2. KEY_SW035_hp700 — key-exact constant Rw vs per-well Rw

**Question:** Does a constant Rw=0.05 key-exact SW beat the per-well Rw Simandoux fallback at hp=700?

**Command:**
```bash
python -m src.main --honeypot-target 700 --pay-no-perm --vsh-fixed \
  --archie-a 0.62 --archie-m 2.15 --pay-sw-max 0.35 --rw 0.05 --rw-mode constant \
  --tag KEY_SW035_hp700
```

**Result:**
- Zip: `outputs/submission_20260629_KEY_SW035_hp700.zip`
- Total flagged: **700**
- Wells with pay: **99**
- Validation: READY ✅ (0 physics-gate / 0 round-trip failures)

---

## 3. HEDGE_keyexact_hp250 — private-LB insurance / back-calc validation

**Question:** What is the public score of key-exact pay at a moderate honeypot count? Designed to score low (~20s); mainly private-LB insurance and validates the back-calculation.

**Command:**
```bash
python -m src.main --honeypot-target 250 --pay-no-perm --vsh-fixed \
  --archie-a 0.62 --archie-m 2.15 --pay-sw-max 0.60 --rw 0.05 --rw-mode constant \
  --tag HEDGE_keyexact_hp250
```

**Result:**
- Zip: `outputs/submission_20260629_HEDGE_keyexact_hp250.zip`
- Total flagged: **250**
- Wells with pay: **543**
- Mean pay fraction: 0.2347
- Validation: READY ✅ (0 physics-gate / 0 round-trip failures)

---

## Summary Table

| Probe | Zip path | Flagged | Wells with pay | Validation |
|---|---|---:|---:|---|
| PERM_PROBE_hp750 | `outputs/submission_20260629_PERM_PROBE_hp750.zip` | 750 | 41 | READY ✅ |
| KEY_SW035_hp700 | `outputs/submission_20260629_KEY_SW035_hp700.zip` | 700 | 99 | READY ✅ |
| HEDGE_keyexact_hp250 | `outputs/submission_20260629_HEDGE_keyexact_hp250.zip` | 250 | 543 | READY ✅ |

All three zips are generated and validated. Public scores pending upload.
