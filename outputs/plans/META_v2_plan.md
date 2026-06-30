# META_v2 Plan — Ideal Metadata Signal for Final Day

**Date:** 2026-06-30  
**Workspace:** `think-onwards-no-second-guessing-kimchi` (main branch)  
**Context:** META_hp650 = 34.44 (+0.54 over plain hp650). Need stronger signal.

## Goal
Build a reusable, comprehensive metadata-leakage detector and use it to push the score above 34.65 on final day.

## Why metadata?
- Physics/population signals are dead (brief §17).
- First metadata bump (DATE format + COMP names) gave measurable lift.
- Synthetic wells likely carry generator fingerprints in headers/parameters/ASCII formatting.

## Architecture

### 1. `src/metadata_detector.py`
Extract file-level features from raw LAS text:
- **Header numeric:** STRT, STOP, STEP, NULL, depth span, row count mismatch
- **Parameter section:** date format/style, COMP, SRVC, WELL, FLD, LOC, param line/byte counts, has ~O
- **Curve section:** num curves, missing primaries, presence of CAL/BIT/PE/SP/RXO/JUNK
- **ASCII data:** decimal-place distribution, trailing-zero fraction, unique-value fraction
- **File-level:** size, line endings, section count, header bytes

### 2. `experiments/analyze_metadata_signal.py`
- Run existing detector on all 800 wells to get hard-veto labels.
- Extract metadata features.
- Compute per-feature AUC / Cohen's d / category lift.
- Train simple combined model (logistic regression / small random forest).
- Output `outputs/metadata_v2_analysis.json` with recommended weights.

### 3. Wire into `src/honeypot_detector.py`
- Replace hand-coded `_metadata_signature` with call to `metadata_detector.metadata_score()`.
- Use analysis-derived weights, capped conservative.
- Keep metadata as **ranking-only** (severity), never hard-veto.

### 4. Build candidates
- `META_v2_hp750` — primary candidate at known knee
- `META_v2_hp650` — fallback if v2 attenuates at high count
- `META_v2_hp700` — middle bracket

## Expected outcome
If v2 signal is 1.5–2× stronger than v1, projected scores:
- hp750: 34.65 + 0.8–1.1 = **35.5–35.8**
- hp650: 33.9 + 0.8–1.1 = **34.7–35.0**

Realistic ceiling with metadata alone: **~36**.

## Risk
- Overfit to public leaderboard generator fingerprints.
- Private holdout may shift date/company distributions.
- Still unlikely to reach 39 without a near-perfect separator.

## 5 final-day slot strategy
1. `META_v2_hp750` — test strongest signal at known knee
2. `META_v2_hp725` or `hp775` — bracket the new knee
3. `META_v2_hp650` — test low-count behavior
4. `META_v2 + key-exact pay` at best count — boost A2 recall
5. Refinement of winning direction
