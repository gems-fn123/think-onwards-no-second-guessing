# PREC_<winning_hp>_sw025 — Pre-registration

**Date:** 2026-06-28
**Branch:** day-3-and-4
**Plan reference:** outputs/plans/day_3_4_5_plan.md §2 (Day-3 Slot 3)

## Hypothesis
If slot 2 won with `sw=0.30`, the footage is still overpredicted. Tightening `PAY_SW_MAX` to `0.25` at the winning honeypot target (from slots 1-2) will find the Jaccard sweet spot without losing the A3 precision gains.

## Target axis
**A2** (footage + Jaccard)

## Expected axis ratio
| axis | expected multiplier |
|---|---|
| A1 | 1.00 |
| A2 | ~1.05 over slot 2 |
| A3 | 1.00 (vs slot 2) |
| A4 | 1.00 |

## Pre-registered acceptance criterion
**score > slot 2 result**

## Pre-registered refutation criterion
**score ≤ slot 2 result** → `sw=0.30` was already at the floor.

## Risk class
**medium** — footage may collapse below 0.04.

## Files to modify
- `src/config.py` (change `PAY_SW_MAX` to 0.25)
- Run with `--honeypot-target <winning_hp>`

## Why this slot
Reactive bracket to find the exact bottom of the `PAY_SW_MAX` curve before consolidating.

## Fallback if refuted
Snap back to `sw=0.30` (or `0.35` if slot 2 failed) for the consolidation in slot 4.

---

## Run record (fill after execution)
**Run command:**
```bash
python3 -m src.main --honeypot-target <winning_hp>
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
