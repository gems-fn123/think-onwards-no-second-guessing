# SKILL: Physics-First Petrophysical Interpretation

This file documents the **agent roles** that make up the No Second Guessing
workflow. Each "agent" is a deterministic Python module in `src/` — there are no
LLM calls in the scored path. The agent framing describes responsibilities and
hand-offs; reproducibility and physical correctness are what the challenge
rewards, so the compute is pure Python.

## Operating principle

Behave like a disciplined petrophysicist, not a classifier. Prefer transparent,
auditable logic with explicit assumptions over fragile thresholds. Separate the
**pay opinion** from the **physics audit**: the pay classifier proposes pay, and
an independent honeypot auditor can veto it. Never let one curve or one fragile
assumption mint pay on its own.

## Agents (module map)

| Agent | Module | Responsibility |
|-------|--------|----------------|
| Ingestion | `src/ingest.py` | Load LAS via lasio (nulls→NaN) **and** capture raw text verbatim for append-preserve writing. |
| Curve mapping | `src/curve_mapping.py` | Resolve 217 messy mnemonics to canonical families by priority; normalize units; null physically impossible samples. |
| QC | `src/qc.py` | Per-well summaries: presence, dead curves, NaN fractions, washout, depth integrity, density-neutron sanity. |
| Petrophysics | `src/petrophysics.py` | VSH, PHIT, PHIE, SW, PERM with robust fallbacks; clamp all outputs; expose pre-clamp diagnostics. |
| Honeypot auditor | `src/honeypot_detector.py` | Well-level suspicion score from cross-curve contradictions; veto whole-well pay to zero when hard physics is violated. |
| Pay classifier | `src/pay_classifier.py` | Multi-criteria conjunction → apparent pay → final pay after veto. Binary, no NaN. |
| LAS writer | `src/las_writer.py` | Append-preserve export: original text untouched, six curves added. |
| Validation | `src/validation.py` | Physics gates + append-preserve round-trip + submission-readiness report. |
| Orchestrator | `src/main.py` | Runs the per-well pipeline, logs, validates, builds the submission zip. |

## Hand-off contract

```
ingest → WellRecord{depth, curves, units, raw_text, canonical}
qc(WellRecord) → QCResult{flags, dead_curves, washout, …}
petrophysics(WellRecord, QCResult) → PetroResult{vsh, phit, phie, sw, perm, diagnostics}
pay.compute_apparent_pay(PetroResult) → apparent_pay, fraction
honeypot.detect(WellRecord, QCResult, PetroResult, apparent_fraction) → HoneypotResult{is_honeypot}
pay.classify(PetroResult, is_honeypot) → PayResult{pay_flag}
las_writer.write_processed(WellRecord, {6 curves}) → processed LAS
validation.validate_curves(...) → WellValidation
```

## Non-negotiable invariants (physics gate)

- All six curves present in every output well.
- `PAY_FLAG ∈ {0,1}` with no NaN.
- `0 ≤ VSH, PHIT, PHIE, SW ≤ 1` and `PHIE ≤ PHIT`.
- `PERM ≥ 0`; no required curve is all-NaN.
- Original columns are preserved byte-for-byte (append-preserve round-trip).

## Risk posture

**Balanced.** Pay requires agreement of shale, porosity, saturation, and
permeability criteria. The honeypot veto is strict (hard physics violations
auto-veto; soft signals must accumulate) so real wells are not zeroed — which
matters because the geometric-mean scoring punishes any zeroed axis.
