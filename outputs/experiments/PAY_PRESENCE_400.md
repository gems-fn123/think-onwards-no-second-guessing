# PAY_PRESENCE_400 — Pre-registration

**Date:** 2026-06-28
**Branch:** day-3-and-4
**Plan reference:** outputs/plans/day_3_4_5_plan.md §2 (Day-3 Slot 5)

## Hypothesis

An explicit well-level pay-presence classifier (e.g. logistic on VSH+PHIE+RT distributions) will improve A2 Jaccard over relying solely on honeypot veto, because it separates "real wells that should have pay" from "real wells that are dry" without zeroing pay on false-positive honeypot flags.

## Target axis

**A2** (Jaccard / pay accuracy)

## Expected axis ratio

| axis | expected multiplier |
|---|---|
| A1 | 1.00 |
| A2 | ≥ 1.10 vs slot-4 consolidation |
| A3 | 1.00 (hp fixed at 400) |
| A4 | 1.00 |

## Pre-registered acceptance criterion

score > slot-4 consolidation result

## Pre-registered refutation criterion

score ≤ slot-4 consolidation result → pay-presence adds noise or does not generalize; abandon Move C.

## Risk class

very high — architectural change to `src/pay_classifier.py`; must preserve validation READY.

## Files to modify

- `src/pay_classifier.py`: add well-level pay-presence model
- `src/config.py`: possible new flags
- `outputs/experiments/PAY_PRESENCE_400.md` (this file)

## Why this slot

Alternative-axis probe. If precision + footage tuning plateau, the remaining A2 headroom may come from modeling pay presence explicitly.

## Fallback if refuted

Abandon pay-presence; day-4 focuses on Move B (A4 hunt) instead.

---

## Run record (fill after execution)

**Run command:**
```
cd /home/gems-fn123/think-onwards-no-second-guessing
python3 -m src.main --honeypot-target 400
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
