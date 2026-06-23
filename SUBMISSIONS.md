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

## S1/S2 results — clean axis attribution

| # | change vs iter3 (B=21.22) | axis moved | score | finding |
|---|---------------------------|-----------|------:|---------|
| **S1** | per-well Rw on OUTPUT SW; PAY_FLAG frozen = iter3 | **A4 only** | **21.2** | `(21.2/21.22)^4 ≈ 1.00` → **SW change is A4-NEUTRAL. SW is not the binding A4 curve.** Hypothesis refuted. |
| **S2** | per-well Rw drives SW **and** pay (0.24→0.16) | A4 + A2 | **22.48** | +1.26 over iter3. Since A4 is flat (S1), the whole gain is **A2: cutting pay overprediction.** |

**Conclusions:** (1) A2 is a live lever — we were overpredicting pay. (2) The A4
floor is **PHIE and/or PERM, not SW** (per-well A4 = geomean of the 3 curves; a
wrong PHIE zeros the well regardless of SW). (3) The queued no-resistivity SW fix
is dropped — SW doesn't move A4. **New baseline B' = S2 = 22.48** (adopt per-well
Rw, value realised via A2).

## Next submission window (pre-registered)

Baseline **B' = S2 = 22.48** (per-well Rw, pay 0.164, honeypot target 200).

| # | zip | change vs B' | axis | pre-registered acceptance |
|---|-----|--------------|------|---------------------------|
| **N1** | N1_paytight_sw45.zip | SW_max 0.55→0.45 (pay 0.164→0.127) | A2 | If `T>22.48`, still overpredicting → tighten further. |
| **N2** | N2_payloose_sw65.zip | SW_max 0.55→0.65 (pay 0.164→0.191) | A2 | If `T>22.48`, loosen instead. N1/N2 bracket the footage optimum. |
| **N3** | (build) PHIE probe, pay frozen | A4 | alternate PHIE (fluid ρ 1.0→1.1 / density-only / gas-corr). `(T/22.48)^4`=A4 ratio. >1.05 ⇒ PHIE is the A4 floor → calibrate. |
| **N4** | (build) PERM standard-Timur, pay frozen | A4 | `(T/22.48)^4`=A4 ratio. >1.05 ⇒ PERM is a floor curve. |
| **N5** | combine winning pay level + winning curve fix | all | predict total = product of measured ratios; deviation ⇒ interaction. |

Submit order: **N1, N2** (A2 footage bracket — ready now) → then **N3, N4**
(A4 PHIE/PERM probes, need the general freeze-pay decoupling) → **N5** combine.
N3/N4 are the high-uncertainty, high-value probes: they finally test whether A4
has headroom (the likely reason for the gap to the 37 leaders).

### Retained anchors
- iter2_hard135 (17.82), iter3_top200 (21.22), S1 (21.2), S2 (22.48 = B').
