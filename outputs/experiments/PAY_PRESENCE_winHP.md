# PAY_PRESENCE_<winning_hp> — Pre-registration

**Date:** 2026-06-28
**Branch:** day-3-and-4
**Plan reference:** outputs/plans/day_3_4_5_plan.md §2 (Day-3 Slot 5)

## Hypothesis
Explicit pay-presence beats reliance on honeypot veto alone for A2 Jaccard (veto zero-out penalises A2 even when the well is real).

## Target axis
**A2** (Jaccard primarily)

## Expected axis ratio
| axis | expected multiplier |
|---|---|
| A1 | 1.00 |
| A2 | > 1.00 vs slot 4 |
| A3 | 1.00 |
| A4 | 1.00 |

## Pre-registered acceptance criterion
**score > slot 4 (consolidation) result**

## Pre-registered refutation criterion
**score ≤ slot 4** → pay-presence adds noise; revert.

## Risk class
**very high** — architectural; needs care to not break validation.

## Files to modify
- `src/pay_classifier.py` (implement well-level pay-presence model)
- Run with `--honeypot-target <winning_hp>`

## Why this slot
Testing explicit pay presence versus relying entirely on honeypot veto for well-level pay decisions.

## Fallback if refuted
Abandon pay-presence; day-4 should focus on Move B (A4 hunt) to find remaining headroom.

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
