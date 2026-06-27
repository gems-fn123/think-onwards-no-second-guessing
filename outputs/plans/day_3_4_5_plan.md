# Day-3 + Day-4 + Day-5 Submission Plan

**Branch:** `day-3-and-4`
**Baseline:** day-2 precision features merged in; `HONEYPOT_TARGET_COUNT = 400`; `PAY_SW_MAX = 0.35`
**Reference score:** **34.52** (CONS = hp700 + sw0.35) on `main`
**Public leader (current):** **39.0**
**Days used:** day-1 (blunt A3 sweep), day-2 (precision pivot), day-3 (this plan starts here)

---

## 1. Strategic frame

Three moves with line-of-sight to 34.52+ (and ultimately to 37+):

| Move | What it bets | Risk | Slots |
|---|---|---|---|
| **A — Precision @ lower hp** | Day-2 precision features catch all 200 honeypots in top-300/400 slots → A3 stays ~100 while A2 recovers from the hp700-suppression level | medium | 2–3 |
| **B — A4 floor hunt** | A4 is suspected saturated but PERM scoring (tol 0.5 log-decades, the widest of the 3 A4 curves) is untested — may have headroom | low–medium | 2 |
| **C — Pay-presence classifier** | Explicit "should-this-well-have-pay" model beats reliance on honeypot veto for A2 Jaccard | medium–high | 2 |

Public leader is **39.0**; the 34.52 gap is ~4.5 points (geomean, ratio⁴ ≈ 2.4 to close).
A single-axis move closing 1.5 points (~36) needs ratio⁴ of one axis ≥ 1.46.

---

## 2. Day-3 — Move A vs Move C face-off (5 slots)

### Slot 1 — Probe 1: `PREC_400_sw035`

| Field | Value |
|---|---|
| Change | Day-2 precision features active (merged in branch), `HONEYPOT_TARGET_COUNT=400` (override via `--honeypot_target 400`), `PAY_SW_MAX=0.35` |
| Hypothesis | Precision features will catch ~all 200 honeypots in the top-400 slots (day-2 finding: +0.22 at hp400 over baseline H3) |
| Target axis | **A3** (precision → enables lower hp) |
| Expected axis ratio | A3 ≈ 95–100; A2 unchanged from baseline at hp400 |
| **Acceptance** | score > 29.91 (baseline H3 at hp400) |
| **Refutation** | score ≤ 29.91 → precision features do not survive merge to our branch; pivot to Move C |
| Risk | low (single-variable: hp override only; precision features already merged) |
| Rationale for slot 1 | Establishes precision-feature floor in new branch before tightening pay or adding architecture |
| Fallback if refuted | Skip slot 2's hp=500 sweep; go straight to pay-presence at hp=700 in slot 5 |

### Slot 2 — Probe 2: `PREC_500_sw030`

| Field | Value |
|---|---|
| Change | Day-2 precision features, `HONEYPOT_TARGET_COUNT=500`, `PAY_SW_MAX=0.30` (tighter pay cutoff) |
| Hypothesis | Tighter pay cutoff + precision features → A2 Jaccard improves without losing A3 |
| Target axis | **A2** (footage + Jaccard) at moderate hp |
| Expected axis ratio | A2 × ~1.1; A3 ≈ flat vs slot 1; A1, A4 unchanged |
| **Acceptance** | score > max(slot 1 result, 30.13 = day-2 H_PRECISION_400) |
| **Refutation** | score ≤ 30.13 AND ratio⁴_A2 < 1.0 → sw=0.30 too tight at this hp |
| Risk | medium (two knobs: hp override + sw override) |
| Rationale for slot 2 | Tests whether tightening pay is the next lever once precision is locked in |
| Fallback if refuted | Revert to sw=0.35 for the rest of day-3; abandon "tighter sw" thread this round |

### Slot 3 — FT1 (reactive bracket): `PREC_<winning_hp>_sw025`

| Field | Value |
|---|---|
| Change | Use whichever hp won in slots 1–2 (likely 400 or 500), push sw even tighter to **0.25** |
| Hypothesis | If slot 2 won with sw=0.30, the footage is still overpredicted → sw=0.25 finds the Jaccard sweet spot |
| Target axis | A2 |
| Expected axis ratio | A2 × ~1.05 over slot 2 |
| **Acceptance** | score > slot 2 result |
| **Refutation** | score ≤ slot 2 result → sw=0.30 was already at the floor |
| Risk | medium (footage may collapse below 0.04) |
| Fallback if refuted | Snap back to sw=0.30 for the consolidation in slot 4 |

### Slot 4 — FT2 (consolidation): `CONS_<winning_hp>_<winning_sw>`

| Field | Value |
|---|---|
| Change | Best (hp, sw) from slots 1–3, with day-2 precision features |
| Hypothesis | Combining the day's winning parameters compounds gains from precision + A2 tightening |
| Target axis | A2 × A3 jointly |
| **Acceptance** | score > 34.52 (current all-time peak) |
| **Refutation** | score ≤ 34.52 → day-3 ceiling at this knob frontier; day-4 must try architectural changes |
| Risk | high (consolidation; multi-knob) |
| Fallback if refuted | Day-4 opens with Move C (pay-presence) instead of Move B (A4 hunt) |

### Slot 5 — FT3 (alternative axis): `PAY_PRESENCE_<winning_hp>`

| Field | Value |
|---|---|
| Change | Add a well-level pay-presence classifier in `src/pay_classifier.py` (e.g. logistic on VSH+PHIE+RT distributions), use it to mark wells that should have *any* pay before honeypot veto; combine with winning (hp, sw) |
| Hypothesis | Explicit pay-presence beats reliance on honeypot veto alone for A2 Jaccard (veto zero-out penalises A2 even when the well is real) |
| Target axis | A2 (Jaccard primarily) |
| **Acceptance** | score > slot 4 (consolidation) result |
| **Refutation** | score ≤ slot 4 → pay-presence adds noise; revert |
| Risk | very high (architectural; needs care to not break validation) |
| Fallback if refuted | Abandon pay-presence; day-4 should focus on Move B (A4 hunt) to find remaining headroom |

**Day-3 decision tree:**
```
                    [Day-3 root: precision features merged, default sw=0.35]
                                  |
                  ┌───────────────┼───────────────┐
            Slot 1: PREC_400     Slot 2: PREC_500     (probes in parallel)
            sw=0.35              sw=0.30
                  |                    |
                  └──────┬─────────────┘
                         v
                Slot 3: tighten sw to 0.25 at winning hp
                         |
                         v
                Slot 4: CONS_<winning_hp>_<winning_sw>
                         |
                         v
                Slot 5: add pay-presence classifier
```
Terminal nodes = the scoreboard after slot 5.

---

## 3. Day-4 — Move B (A4 hunt) + consolidation (5 slots)

Day-4 inputs come from day-3 outcomes. The two probes (slots 6, 7) run in parallel after day-3 closes.

### Slot 6 — Probe 1: `A4_PERM_RECAL_<day3_best_hp>`

| Field | Value |
|---|---|
| Change | Recalibrate PERM Timur coefficients in `src/config.py` (`PERM_A=-2.0 → -1.8`, `PERM_B=16.0 → 18.0`, `PERM_C=3.0 → 2.5`), **freeze PAY_FLAG** to day-3's best config (decouple per methodology rule #3), hp = day-3 winning |
| Hypothesis | PERM scoring tolerance (0.5 log-decades, the widest of the 3 A4 curves) might be the floor |
| Target axis | **A4** (specifically the PERM curve) |
| Expected axis ratio | A4 × ~1.05; A1, A2, A3 unchanged (pay frozen) |
| **Acceptance** | ratio⁴_A4 > 1.0 AND score ≥ day-3 best (no A2/A3 regression from frozen pay) |
| **Refutation** | ratio⁴_A4 ≤ 1.0 → A4 PERM floor does not respond to Timur tuning in this range |
| Risk | medium (multi-knob PERM change; pay-frozen isolates A4) |
| Fallback if refuted | Day-4 slot 7 falls back to A4 SW recalibration |

### Slot 7 — Probe 2: `A4_PHIE_NEUTRON_ONLY_<day3_best_hp>`

| Field | Value |
|---|---|
| Change | Force PHIT method to **neutron-only** (skip density averaging), pay frozen, hp = day-3 winning |
| Hypothesis | The density-neutron average clips both inputs; one of the components may match the key better than the average |
| Target axis | A4 (PHIE curve) |
| Expected axis ratio | A4 × ~1.03 |
| **Acceptance** | ratio⁴_A4 > 1.0 |
| **Refutation** | ratio⁴_A4 ≤ 1.0 → the averaging is correct, individual components aren't better |
| Risk | low (single-knob; pay-frozen) |
| Fallback if refuted | Skip A4 hunting; day-4 slots 8–9 pivot to consolidating day-3 wins across multiple hp variants |

### Slot 8 — FT1 (reactive bracket): `A4_WINNER_<day3_best_hp>_<alt_hp>`

| Field | Value |
|---|---|
| Change | If slot 6 won → apply same PERM coeffs at hp=300 (lower, to recover A2 with A4 boost). If slot 7 won → apply neutron-only PHIT at the same alt hp. |
| Hypothesis | The A4 gain compounds with the A2 gain from lower hp |
| Target axis | A4 × A2 jointly |
| **Acceptance** | score > max(slot 6 result, slot 7 result, day-3 best) |
| **Refutation** | score ≤ best so far |
| Risk | medium (two-knob: A4 lever + hp override) |
| Fallback if refuted | Lock in the A4 winner at day-3's best hp; no hp change |

### Slot 9 — FT2 (consolidation): `CONS_BEST_ALL_<best_hp>`

| Field | Value |
|---|---|
| Change | If slot 8 won: combine its A4 lever + day-3 best hp/sw/precision features. If slot 8 lost: use slot 6 or 7 result alone at day-3 best hp |
| Hypothesis | Consolidation of all winning knobs into a single submission reaches the day's ceiling |
| Target axis | A2 × A3 × A4 jointly |
| **Acceptance** | score > 34.52 (or the best day-3 result if it already beat 34.52) |
| **Refutation** | score ≤ 34.52 AND ≤ day-3 best → we have found the ceiling of this knob frontier |
| Risk | high (consolidation) |
| Fallback if refuted | Day-5 plans A/B/C below may need to drop the A4 lever and rely on day-3 alone |

### Slot 10 — FT3 (private-holdout hedge): `HEDGE_KEYALIGNED_<day3_best_hp>`

| Field | Value |
|---|---|
| Change | Revert to key-aligned formulas: `ARCHIE_A=0.62`, `ARCHIE_M=2.15`, fixed VSH endpoints (20/120 GAPI), keep `PAY_USE_PERM=False` and `PAY_SW_MAX=0.35`. hp = day-3 best. NO day-2 precision features. |
| Hypothesis | The reff says final ranking is on private holdout. Mechanism alignment is the tie-break; if public-best is overfitted, the key-aligned config protects the private score |
| Target axis | Mechanism robustness (no single axis target) |
| Expected axis ratio | Score likely lower than day-3 best (M3 ratio⁴=0.983 → ~−0.6 points) |
| **Acceptance** | score > 32.0 (≥ 93% of best — defends private if public overfits) |
| **Refutation** | score ≤ 32.0 → even mechanism-aligned underperforms |
| Risk | medium (multi-knob revert; each knob documented in M3 history) |
| Fallback if refuted | Day-5 drops the hedge slot; relies entirely on day-3/day-4 winners |

**Day-4 decision tree:**
```
                    [Day-4 root: best day-3 config known]
                                  |
                  ┌───────────────┼───────────────┐
            Slot 6: A4_PERM      Slot 7: A4_PHIE     (probes in parallel)
                  |                    |
                  └──────┬─────────────┘
                         v
                Slot 8: winning A4 lever × alt hp
                         |
                         v
                Slot 9: CONS_BEST_ALL
                         |
                         v
                Slot 10: HEDGE_KEYALIGNED (private safety)
```

---

## 4. Day-5 — Final push: terminal branches only

Day-5 will not run probes. It will submit the surviving terminal branches from the day-3+day-4 decision tree. The exact set depends on what wins, but the candidate set is:

| Slot | Submission | What it tests | When selected |
|---|---|---|---|
| 11 | `FINAL_PUBLIC_BEST` | Day-3 or Day-4 highest-scoring config, re-submitted to confirm reproducibility | Always |
| 12 | `FINAL_PUBLIC_BEST_<lower_hp>` | Same winning config but hp = (winning hp − 200) to recover A2 for private holdout | If day-4 A4 winner or consolidation showed the ceiling wasn't hp-driven |
| 13 | `FINAL_DAY3_BEST` | Day-3 consolidation winner alone (precision + tighter sw, no A4 hunt) | If day-4 failed to find A4 headroom |
| 14 | `FINAL_A4_BEST` | Day-4 A4 winner alone (with day-3 precision features) | If day-4 found A4 headroom |
| 15 | `FINAL_HEDGE` | HEDGE_KEYALIGNED result from day-4 slot 10 (or its tweaked variant) | Always — private-holdout insurance |

**The day-5 set is fully determined by day-3 + day-4 outcomes.** No new probes. Each submission in day-5 is a re-submission or a parametric variant of a known winner.

---

## 5. Pre-execution protocol (every submission)

Per the project's own `petrophysics-tuner.agent.md`:

1. **Write `outputs/experiments/<id>.md` BEFORE any code change** (template in `outputs/experiments/_template.md`)
2. **Run pipeline** with `--limit 1` smoke test, then full run
3. **Validate** `outputs/validation_report.md` reads **READY** (0 physics-gate failures, 0 round-trip failures). If not: fix or revert, do not submit.
4. **Append to scoreboard:** `SUBMISSIONS.md` (prose + scoreboard table) and `outputs/dashboard/submissions.json` (machine-readable)
5. **Commit** on `day-3-and-4` branch with message `<id>: <one-sentence result>`
6. **Update this plan doc** with the actual outcome and the day-5 selection state

---

## 6. Axis math reminder

```
ratio⁴ = (score / anchor)^4
34.52 → 36.0 needs ratio⁴ = (36/34.52)^4 = 1.181   (+18%)
34.52 → 37.0 needs ratio⁴ = (37/34.52)^4 = 1.318   (+32%)
34.52 → 39.0 needs ratio⁴ = (39/34.52)^4 = 1.625   (+63%)
```

Public leader is 39.0 — closing that gap requires multi-axis gains (no single-axis probe can close 4.5 points alone). The 10-submission plan is designed to find at least one axis with > 1.3× ratio per probe; consolidation bets that the gains compound.

---

*Plan authored: 2026-06-27. Branch: `day-3-and-4` at commit 4246113. Authoritative source of truth for the next 15 submission slots.*
