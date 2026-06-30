# Workflow & Tuning Loop

## End-to-end stages

1. **Ingestion** (`ingest.py`) — read each LAS twice: lasio for values
   (nulls→NaN), raw text for byte-exact preservation.
2. **Curve mapping** (`curve_mapping.py`) — resolve mnemonics to canonical
   families by priority; convert units; null physically impossible samples.
3. **QC** (`qc.py`) — per-well flags: presence, dead curves, NaN fraction,
   washout, depth integrity, density-neutron sanity.
4. **Petrophysics** (`petrophysics.py`) — VSH → PHIT → PHIE → SW → PERM with
   fallbacks; clamp everything; keep pre-clamp diagnostics.
5. **Apparent pay** (`pay_classifier.py`) — multi-criteria conjunction.
6. **Honeypot audit** (`honeypot_detector.py`) — well-level suspicion score;
   veto to zero pay on hard physics violations.
7. **Final pay** — apparent pay with the veto applied (binary, no NaN).
8. **Export** (`las_writer.py`) — append-preserve write.
9. **Validation** (`validation.py`) — physics gates + round-trip + report.
10. **Package** (`main.py`) — logs, QC reports, `submission_<date>.zip`.

## Build order (achieved)

- **Goal 1 — valid output for 100% of wells.** ✅ 800/800 written, 0 errors.
- **Goal 2 — pass physics gates.** ✅ 0 gate failures, 0 round-trip failures.
- **Goal 3 — honeypot rejection after QC.** ✅ well-level veto on hard physics
  violations.
- **Goal 4 — iterate thresholds via leaderboard** without overfitting public
  score (below).

## Tuning loop (leaderboard-driven)

All knobs are in [`src/config.py`](../src/config.py). Change one group at a time,
re-run `python -m src.main`, submit, observe which axis moved.

| If this axis is low | Adjust | Direction |
|---------------------|--------|-----------|
| Physics gate | (should never fail) | inspect `validation_report.md` |
| Pay accuracy | `PAY_*` cutoffs | tighten to raise precision, loosen to raise recall |
| Honeypot rejection | `HONEYPOT_*` weights / threshold | lower threshold = veto more wells |
| Curve accuracy | `RHO_MA_*`, `RW_*`, `ARCHIE_*`, `PERM_*` | match regional expectations |

Guardrails:

- Keep the honeypot veto strict enough that genuine wells are not zeroed (the
  geometric mean punishes a near-zero pay axis harder than a slightly imperfect
  one).
- Change cutoffs in small steps; large public-score swings usually mean
  overfitting, not improvement.
- Re-run the full validation after every change — never submit a zip whose
  `validation_report.md` verdict is not `READY`.

## Diagnostics to watch (current run)

- `outputs/validation_report.md` — must read **READY**.
- `outputs/run_logs/run_*.csv` — per-well methods, honeypot score, pay fraction.
- `outputs/qc_reports/honeypot_flags.csv` — which wells were vetoed and why.
- Mean pay fraction and honeypot count — sanity-check they are neither ~0 nor
  ~all.
