# Pre-Registration Template

Copy this file to `outputs/experiments/<submission_id>.md` and fill in all fields BEFORE making any code change.

---

# <submission_id> — Pre-registration

**Date:** YYYY-MM-DD
**Branch:** day-3-and-4
**Plan reference:** outputs/plans/day_3_4_5_plan.md §<slot>

## Hypothesis

<one sentence: what we believe will happen and why>

## Target axis

A1 / A2 / A3 / A4 (circle one)

## Expected axis ratio

| axis | expected multiplier |
|---|---|
| A1 | 1.00 |
| A2 | <value> |
| A3 | <value> |
| A4 | <value> |

## Pre-registered acceptance criterion

score > <anchor score> at <parameter config>

## Pre-registered refutation criterion

score ≤ <anchor score> AND ratio⁴_<target axis> ≤ 1.0

## Risk class

low / medium / high — and why

## Files to modify

- <list each file>

## Why this slot

<rationale for placement in the day-3/4 plan>

## Fallback if refuted

<what we do next based on this outcome>

---

## Run record (fill after execution)

**Run command:**
```
cd /home/gems-fn123/think-onwards-no-second-guessing
python3 -m src.main --honeypot_target <N> [--other flags]
```

**Validation verdict:** READY ✅ / FAILED ❌

**Score:** <number>

**Axis ratio (vs anchor):**
- A1 ×
- A2 ×
- A3 ×
- A4 ×

**Verdict:** win / flat / loss

**One-sentence interpretation:** <>

**Commit:** `<commit-hash>: <message>`

---

*Pre-registration is binding. If reality departs from the registered hypothesis in a meaningful way, document why in the run record and proceed — do not silently rewrite the hypothesis.*
