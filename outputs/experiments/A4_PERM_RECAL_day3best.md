# A4_PERM_RECAL_<day3_best_hp> — Pre-registration

**Date:** 2026-06-28
**Branch:** day-3-and-4
**Plan reference:** outputs/plans/day_3_4_5_plan.md §3 (Day-4 Slot 6)

## Hypothesis
PERM scoring tolerance (0.5 log-decades, the widest of the 3 A4 curves) might be the floor. Recalibrating PERM Timur coefficients (`PERM_A=-1.8`, `PERM_B=18.0`, `PERM_C=2.5`) with frozen `PAY_FLAG` isolates A4 and finds headroom.

## Target axis
**A4** (specifically the PERM curve)

## Expected axis ratio
| axis | expected multiplier |
|---|---|
| A1 | 1.00 |
| A2 | 1.00 (pay frozen) |
| A3 | 1.00 (pay frozen) |
| A4 | ~1.05 |

## Pre-registered acceptance criterion
**ratio⁴_A4 > 1.0 AND score ≥ day-3 best**

## Pre-registered refutation criterion
**ratio⁴_A4 ≤ 1.0** → A4 PERM floor does not respond to Timur tuning in this range.

## Risk class
**medium** — multi-knob PERM change; pay-frozen isolates A4.

## Files to modify
- `src/config.py` (change PERM coeffs, freeze PAY_FLAG)
- Run with `--honeypot-target <day3_best_hp>`

## Why this slot
Testing if A4 is truly saturated or if PERM has headroom.

## Fallback if refuted
Day-4 slot 7 falls back to A4 PHIE recalibration.

---

## Run record (fill after execution)
**Run command:**
```bash
python3 -m src.main --honeypot-target <day3_best_hp>
```
**Validation verdict:** _pending_
**Score:** _pending_
**Axis ratio:**
- A1 × _pending_
- A2 × _pending_
- A3 × _pending_
- A4 × _pending_
**Verdict:** _pending_
**One-sentence interpretation:** _pending_
**Commit:** _pending_
