# CONS_<winning_hp>_<winning_sw> — Pre-registration

**Date:** 2026-06-28
**Branch:** day-3-and-4
**Plan reference:** outputs/plans/day_3_4_5_plan.md §2 (Day-3 Slot 4)

## Hypothesis
Combining the day's winning parameters compounds gains from precision + A2 tightening.

## Target axis
**A2 × A3 jointly**

## Expected axis ratio
| axis | expected multiplier |
|---|---|
| A1 | 1.00 |
| A2 | > 1.00 (from winning sw) |
| A3 | > 1.00 (from winning hp + precision) |
| A4 | 1.00 |

## Pre-registered acceptance criterion
**score > 34.52** (current all-time peak)

## Pre-registered refutation criterion
**score ≤ 34.52** → day-3 ceiling at this knob frontier; day-4 must try architectural changes.

## Risk class
**high** — consolidation; multi-knob.

## Files to modify
- `src/config.py` (change `PAY_SW_MAX` to winning sw)
- Run with `--honeypot-target <winning_hp>`

## Why this slot
Lock in the day-3 high.

## Fallback if refuted
Day-4 opens with Move C (pay-presence) instead of Move B (A4 hunt).

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
