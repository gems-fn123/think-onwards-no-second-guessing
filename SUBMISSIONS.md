# Submission Diagnostic Log

Public leaderboard scores per submission. Scoring = geometric mean of 4 axes
(A1 gates, A2 pay, A3 honeypot = `100*(caught/200)^2`, A4 curve). 800 wells =
600 real + 200 honeypots.

| iter | zip | honeypot target | flagged | pay wells | mean pay frac | matrix | PHIE_min / SW_max | RW | public score | Δ |
|------|-----|----------------:|--------:|----------:|--------------:|--------|-------------------|----|-------------:|----|
| 1 | (baseline) | threshold 3.0 | 61 | 779 | 0.32 | PE (dolomite on 185) | 0.08 / 0.60 | 0.05 | **15.03** | — |
| 2 | submission_20260623_iter2_hard135.zip | 0 (hard only) | 135 | 655 | 0.26 | sandstone | 0.10 / 0.55 | 0.05 | **17.82** | +2.79 |
| 3 | submission_20260623_iter3_top200.zip | 200 | 200 | 593 | 0.24 | sandstone | 0.10 / 0.55 | 0.05 | **21.22** | +3.40 |

## Reading

- **iter1→iter2 (+2.79):** sandstone matrix (fixes PHIE on 185 wells → A4) +
  raw-OOB honeypot detector (61→135 → A3) + tighter pay (→ A2). Bundled.
- **iter2→iter3 (+3.40):** honeypot recall 135→200 only. Biggest single gain.
  Confirms A3 (squared) is the dominant lever and the 65 suspicion-filled wells
  were net positive (A3 gain > A2 loss).

## Implications for next iterations

- A3 caught is monotonic in #flagged (can only catch more of the 200). Flagging
  extra **real** wells costs A2 only if they are genuinely paying; **dry** real
  wells are free. So overshooting target past 200 may still raise the total →
  test 250 / 300.
- Better suspicion **ranking** (precision) raises A3 without raising count → add
  discriminative physics features.
- A4 still uncalibrated: `RW_DEFAULT=0.05` (SW) and Timur coeffs (PERM) are
  guesses → sweep RW (0.03 / 0.05 / 0.08).
- A2: pay footage still ~0.24 on real wells → may still overpredict.

## Candidates queued (awaiting score)

Marginal-band check: suspicion rank 200–250 has higher apparent pay (0.31) than
rank 135–200 (0.19) → overshoot past 200 starts zeroing wells that look like real
pay (A2 risk). So 200 (= known honeypot count) is likely near-optimal on count;
priority shifts to A4 (Rw) and ranking precision.

Recommended submit order:

| priority | zip | change vs iter3 | hypothesis |
|---------:|-----|-----------------|-----------|
| 1 | submission_20260623_iter5_rw0.03.zip | RW 0.05→0.03 (SW↓, pay 0.24→0.28) | A4: truth SW may be lower |
| 1 | submission_20260623_iter5_rw0.08.zip | RW 0.05→0.08 (SW↑, pay 0.24→0.20) | A4: truth SW may be higher |
| 3 | submission_20260623_iter4_top250.zip | flag 200→250 | overshoot (likely marginal/neg) |
| 4 | submission_20260623_iter4_top300.zip | flag 200→300 | overshoot upper bound |

After Rw direction is known: refine net-pay cutoffs (A2) and add discriminative
physics features to lift suspicion-ranking precision (A3 without raising count).
