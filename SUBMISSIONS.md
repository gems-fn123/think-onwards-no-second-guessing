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

## Active candidates (pre-registered, awaiting score)

After the data-scientist review + targeted diagnostics (see DECISION_QUALITY.md):
the binding axes are A2/A4 (likely single digits), not honeypot count. Data-implied
Rw ≈ 0.14 vs our 0.05. Blind global-Rw and severity-overshoot zips were CLEANED
(superseded — see below).

| # | zip | change vs iter3 (B=21.22) | axis moved | pre-registered acceptance |
|---|-----|---------------------------|-----------|---------------------------|
| **S1** | submission_20260623_S1_rwperwell_decoupled.zip | per-well data-derived Rw on OUTPUT SW; **PAY_FLAG frozen = iter3** (verified byte-identical) | **A4 only** | `(T_S1/21.22)^4` = A4 ratio. Expect T_S1 > 21.22 (Rw 0.05→~0.14 fixes SW). If ≤, Rwa prior wrong or SW not the A4 floor. |
| **S2** | submission_20260623_S2_rwperwell_coupled.zip | per-well Rw drives SW **and** pay (pay 0.24→0.16) | A4 + A2 | Expect T_S2 ≥ S1 if overprediction was also hurting A2. If T_S2 < S1, pay cut too far. |

Submit **S1 first** (clean A4 read), then **S2**. The pair separates the A4 gain
(S1) from the additional A2 effect of the resulting pay reduction (S2 vs S1).

### Cleaned (removed) — superseded, do not submit
- iter5_rw0.03 / iter5_rw0.08 — blind GLOBAL Rw guesses; replaced by per-well data-derived Rw (S1/S2).
- iter4_top250 / iter4_top300 — blind severity-rank overshoot; marginal-band analysis says count ≈200 is near-optimal; future overshoot (S4) will use residual ranking, not severity.

### Retained
- iter2_hard135 (17.82) and iter3_top200 (21.22) — scored anchors / current baseline B.
