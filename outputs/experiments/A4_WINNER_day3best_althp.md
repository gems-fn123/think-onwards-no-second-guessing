# A4_WINNER_<day3_best_hp>_<alt_hp> — Pre-registration

**Date:** 2026-06-28
**Branch:** day-3-and-4
**Plan reference:** outputs/plans/day_3_4_5_plan.md §3 (Day-4 Slot 8)

## Hypothesis
The A4 gain compounds with the A2 gain from lower hp.

## Target axis
**A4 × A2 jointly**

## Expected axis ratio
| axis | expected multiplier |
|---|---|
| A1 | 1.00 |
| A2 | > 1.00 |
| A3 | > 1.00 |
| A4 | > 1.00 |

## Pre-registered acceptance criterion
**score > max(slot 6 result, slot 7 result, day-3 best)**

## Pre-registered refutation criterion
**score ≤ best so far**

## Risk class
**medium** — two-knob: A4 lever + hp override.

## Files to modify
- `src/config.py` (apply winning A4 lever)
- Run with `--honeypot-target <alt_hp>`

## Why this slot
Reactive bracket to see if A4 gains compound at a different hp.

## Fallback if refuted
Lock in the A4 winner at day-3's best hp; no hp change.

---

## Run record (fill after execution)
**Run command:**
```bash
python3 -m src.main --honeypot-target <alt_hp>
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
