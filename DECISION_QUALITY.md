# Methodological Decision-Quality Assessment

Framework for spending the remaining submission budget rationally, after a
data-scientist review of the first 3 submissions (15.03 → 17.82 → 21.22).

## 0. The reframe

The leaderboard returns ONE number that is the geometric mean of four hidden
axes: `Total = (A1·A2·A3·A4)^(1/4)`. Fractional leverage is **equal across
axes** — a 10% relative gain on any axis moves the total the same amount. The
A3 squaring sets A3's *level*, not its marginal leverage.

Back-of-envelope from our own score: with A1≈95 (clamped) and Total=21.22,
`A2·A3·A4 ≈ 2140`. If A3 were maxed (100), then `geomean(A2,A4) ≈ 4.6`. So
**A2 and A4 are almost certainly single digits — they are the binding
constraint, not honeypot count.** The gap to the leader (37.4) needs ~9.6×
product improvement: that is "a whole axis is near-broken," not "tune a knob."

Three submissions each changed multiple variables, so every per-change magnitude
in `SUBMISSIONS.md` is an inferred story, not a measured effect. **"Flagged 200"
is not "caught 200"** — our own analysis shows ~128 honeypots don't separate.

## 1. Targeted diagnostic findings (offline, no submission spent)

- **G1 coverage/NaN audit (A4 hard-zero risk): CLEAR.** Only 1/800 wells has a
  required curve >50% NaN over its data rows. A4 is not being structurally
  hard-zeroed by gaps. (Our SW/PERM null-mirroring is safe.)
- **Rw is the A4 smoking gun.** Data-implied Rw (Rwa-minimum estimator over clean
  low-VSH zones) = **median 0.14 ohm·m** (p25 0.06, p75 0.47). We use
  `RW_DEFAULT=0.05` — ~3× too low. Low Rw → SW too low (too much apparent HC) →
  SW error >> 0.10 tolerance → **SW curve likely zeroing A4 on many real wells**,
  and overpredicting pay (A2). Highest-confidence, label-free lever.
- **17 no-resistivity wells output SW≈1.0 flat.** If real with pay, SW wrong by
  ~0.7 → A4=0 on those wells. Needs a better SW fallback than flat wet.
- **PERM magnitude is sane** (apparent-pay p50≈7 mD, p25 0.5, p75 76, 1% at
  clamp) — not the catastrophic A4 floor. Functional form still unverified.
- **Honeypot precision is fundamentally capped (G2).** Multivariate Mahalanobis
  on physics-residual features (triple-porosity over-determination, Pickett
  scatter, GR–PHIE decoupling, roughness) is **unimodal — no break at 25%/200.**
  ~72 are cleanly separable (raw OOB); the rest blend into the real manifold.
  A3 recall realistically caps around 60–75% → A3 ≈ 36–56, not 100.

**Conclusion:** stop treating honeypot count as the lever. The next gains are
A4 (Rw, data-derived) and A2 (overprediction), with honeypot work shifting to
*precision at fixed count ~200* via residual features.

## 2. Decision-quality rules (install now)

1. **Pre-register every submission BEFORE seeing the score:** hypothesis, the
   axis it should move, expected total Δ, and the acceptance/refute criterion.
   A surprise then teaches; a post-hoc "reading" only rationalizes.
2. **Single-variable submissions only.** Bundled changes give direction, never
   magnitude. Back out an axis with the ratio identity:
   `A_k^P / A_k^B = (Total_P / Total_B)^4` (valid only if exactly axis k moved).
3. **Decouple calibration from the pay decision** (the key trick): to measure A4
   cleanly, write the recalibrated curve but **freeze PAY_FLAG to the baseline**,
   so A2/A3 are pinned and only A4 moves. NOTE: **A4 is scored at the answer
   key's true pay depths, so it is independent of our PAY_FLAG entirely** — pay
   tuning is automatically A4-clean.
4. **Don't select on public score alone.** Public is a hidden subset; final rank
   uses the private score of your best *public* submission. Under A3 squaring,
   overfitting public honeypots can crater private. Tie-break toward
   mechanism-based, physically-conservative choices over threshold-fitted ones.
5. **Currency = information gain about the binding axis,** not expected points.
   Spend the first ~6 submissions diagnostic, then exploit the remaining ~60.

## 3. Offline work before submitting (free, highest ROI)

- **A4-1 (do first): data-derived Rw.** Replace the global `RW_DEFAULT=0.05` with
  a **per-well Rw from the Rwa-minimum / Pickett estimator** (clamp to a sane
  band, e.g. 0.02–0.6). Re-run; expect SW up, pay down, less overprediction.
- **A4-2: fix the 17 no-resistivity wells** — replace flat SW=1.0 with a
  porosity/regional SW estimate (or carry an Rwa-implied SW) so those wells stop
  scoring A4=0.
- **A3-precision: residual honeypot detector.** Fold the triple-porosity,
  Pickett-scatter, and GR–PHIE-decoupling residuals into the suspicion score;
  keep count ~200 but improve *membership* (swap the weakest severity picks for
  the residual outliers). Validate by feature-subset stability, not labels.

## 4. Pre-registered experiment ladder (next submissions)

Each is single-variable with a written acceptance test. `B` = current best (iter3, 21.22).

| # | Change (everything else = B) | Moves | Pre-registered acceptance |
|---|------------------------------|-------|---------------------------|
| S1 | **Per-well data-derived Rw**, PAY_FLAG frozen to B | A4 only | `(T/21.22)^4` = A4 ratio. Expect > 1 (Rw 0.05→~0.14 fixes SW). If ≤1, Rwa prior wrong or SW isn't the A4 floor. |
| S2 | Per-well Rw + let pay re-derive (SW↑→less pay) | A2+A3 | Expect ≥ S1 if overprediction was hurting A2. If < S1, pay cut too far. |
| S3 | Honeypot **membership swap** at fixed count 200 (residual picks ↔ weakest severity picks) | A3 precision | If `T>21.22` at equal count, residual set is purer → adopt. Else revert. |
| S4 | Overshoot 200→250 by residual rank | A3 count vs A2 | If `T>` B, catchable honeypots remain past 200; else freeze count at 200. |
| S5 | PERM standard-Timur form, pay frozen | A4 only | If A4 ratio >1.1, PERM was a floor curve; else PERM fine. |
| S6 | Best-combined (winning Rw + honeypot set + pay cutoff + PERM) | all | Predict total = product of measured ratios; deviation ⇒ axis interaction. |

After S1–S6 we hold per-axis ratios instead of one fused number, with ~60
submissions left to exploit.

## 5. Statistically questionable items being retired

- "Flagged 200 = caught 200" (recall ≪ 200; padding with real wells).
- Per-change magnitudes read off bundled submissions.
- Fixed-threshold contradiction flags on a look-real manifold → replaced by
  continuous population-relative residuals.
- Univariate suspicion ranking on unimodal features → multivariate residual
  Mahalanobis (still capped, but better precision than severity-only).
- RW sweep with pay coupled to RW → use freeze-pay decoupling for a clean read.
