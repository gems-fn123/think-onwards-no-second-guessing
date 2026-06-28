# PAY_PRESENCE_500 — Pre-registration

**Date:** 2026-06-28
**Branch:** day-3-and-4
**Plan reference:** outputs/plans/day_3_4_5_plan.md §2 (Day-3 Slot 5)

## Hypothesis

An explicit well-level pay-presence classifier at hp=500 will improve A2 Jaccard over honeypot-veto-only pay, while preserving A3 recall at the higher count.

## Target axis

**A2** (Jaccard / pay accuracy)

## Expected axis ratio

| axis | expected multiplier |
|---|---|
| A1 | 1.00 |
| A2 | ≥ 1.10 vs slot-4 consolidation |
| A3 | 1.00 (hp fixed at 500) |
| A4 | 1.00 |

## Pre-registered acceptance criterion

score > slot-4 consolidation result

## Pre-registered refutation criterion

score ≤ slot-4 consolidation result → pay-presence does not help; abandon Move C.

## Risk class

very high — architectural change to `src/pay_classifier.py`.

## Files to modify

- `src/pay_classifier.py`: add well-level pay-presence model
- `src/config.py`: possible new flags
- `outputs/experiments/PAY_PRESENCE_500.md` (this file)

## Why this slot

Alternative-axis probe if hp=500 wins the day.

## Fallback if refuted

Abandon pay-presence; day-4 focuses on Move B (A4 hunt).

---

## Run record (fill after execution)

**Run command:**
```
cd /home/gems-fn123/think-onwards-no-second-guessing
python3 -m src.main --honeypot-target 500
```

**Validation verdict:** _pending_

**Score:** _pending_

**Axis ratio (vs slot-4 consolidation):**
- A1 × _pending_
- A2 × _pending_
- A3 × _pending_
- A4 × _pending_

**Verdict:** _pending_

**One-sentence interpretation:** _pending_

**Commit:** _pending_

---

*Pre-registration binding. Authored 2026-06-28 before any code change on the day-3-and-4 branch.*
