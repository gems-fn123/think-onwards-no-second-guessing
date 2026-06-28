# A4_PHIE_NEUTRON_ONLY_<day3_best_hp> — Pre-registration

**Date:** 2026-06-28
**Branch:** day-3-and-4
**Plan reference:** outputs/plans/day_3_4_5_plan.md §3 (Day-4 Slot 7)

## Hypothesis
The density-neutron average clips both inputs; one of the components (neutron-only) may match the key better than the average.

## Target axis
**A4** (PHIE curve)

## Expected axis ratio
| axis | expected multiplier |
|---|---|
| A1 | 1.00 |
| A2 | 1.00 (pay frozen) |
| A3 | 1.00 (pay frozen) |
| A4 | ~1.03 |

## Pre-registered acceptance criterion
**ratio⁴_A4 > 1.0**

## Pre-registered refutation criterion
**ratio⁴_A4 ≤ 1.0** → the averaging is correct, individual components aren't better.

## Risk class
**low** — single-knob; pay-frozen.

## Files to modify
- `src/config.py` (force PHIT method to neutron-only, freeze PAY_FLAG)
- Run with `--honeypot-target <day3_best_hp>`

## Why this slot
Testing the other A4 curve (PHIE) for headroom.

## Fallback if refuted
Skip A4 hunting; day-4 slots 8–9 pivot to consolidating day-3 wins.

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
