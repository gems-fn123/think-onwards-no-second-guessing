# PRECISION_v2 — Precision-count curve on main

**Date:** 2026-06-29  
**Branch:** main  
**Baseline for comparison:** `COUNT_KNEE_hp750 = 34.65` (same pay config)

## Motivation

`PRECISION_v1` was built with `--honeypot-target N --tag` only, so pay used the config-default Archie parameters (`a=1.0`, `m=2.0`) and non-fixed VSH. That confounded the scores against the clean `COUNT_KNEE_hp750` baseline. `PRECISION_v2` fixes the pay config to exactly match `COUNT_KNEE_hp750`; the only differences are (a) the precision ranking and (b) the count `N`.

## Command template

```bash
python -m src.main --honeypot-target N --pay-no-perm --vsh-fixed \
  --archie-a 0.62 --archie-m 2.15 --pay-sw-max 0.35 --tag PRECISION_v2_hpN
```

for `N` in `400 450 500 550 600`.

## Results

| Submission | File path | Total flagged | Wells with pay | Mean pay fraction | Validation |
|---|---|---:|---:|---:|---|
| `PRECISION_v2_hp400` | `outputs/submission_20260629_PRECISION_v2_hp400.zip` | 400 | 353 | 0.0557 | READY ✅ (0 / 0) |
| `PRECISION_v2_hp450` | `outputs/submission_20260629_PRECISION_v2_hp450.zip` | 450 | 306 | 0.0495 | READY ✅ (0 / 0) |
| `PRECISION_v2_hp500` | `outputs/submission_20260629_PRECISION_v2_hp500.zip` | 500 | 260 | 0.0427 | READY ✅ (0 / 0) |
| `PRECISION_v2_hp550` | `outputs/submission_20260629_PRECISION_v2_hp550.zip` | 550 | 212 | 0.0347 | READY ✅ (0 / 0) |
| `PRECISION_v2_hp600` | `outputs/submission_20260629_PRECISION_v2_hp600.zip` | 600 | 168 | 0.0271 | READY ✅ (0 / 0) |

All submissions passed physics-gate and round-trip validation with zero failures.

## Notes

- Zip binaries are gitignored and were **not** committed to `main`.
- `PRECISION_v1` zip binaries (`hp300`, `hp400`, `hp500`) were removed from git tracking in commit `cbfecbe` to reduce repo bloat.
- Public scores pending upload.
