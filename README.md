# No Second Guessing — Petrophysical Agent

A reproducible, **physics-first** pipeline that ingests raw, unconditioned LAS
well logs and produces a complete petrophysical interpretation suite for every
well, for the ThinkOnward *No Second Guessing* challenge.

For each input well it appends six curves and writes one processed LAS:

| Curve | Meaning | Range |
|-------|---------|-------|
| `VSH` | Volume of shale | 0–1 |
| `PHIT` | Total porosity | 0–1 |
| `PHIE` | Effective porosity | 0–`PHIT` |
| `SW` | Water saturation | 0–1 |
| `PERM` | Permeability (mD) | ≥ 0 |
| `PAY_FLAG` | Binary net-pay indicator | 0 or 1 |

The challenge scores four equally-weighted axes combined with a **geometric
mean** — physics-gate compliance, pay accuracy, honeypot rejection, and curve
accuracy — so a zero on any axis collapses the total. Every design choice here
is biased toward *never zeroing an axis*.

## Why this design

Profiling all 800 evaluation wells up front drove the architecture:

- The provided **submission sample is a byte-identical copy of the inputs** and
  contains **no labels** anywhere. This is an **unsupervised, deterministic
  petrophysics** problem — there is nothing to train an ML model on. The agent
  behaves like a disciplined petrophysicist, not a black box.
- Headers are messy: **217 distinct mnemonics**, heavy aliasing, inconsistent
  units (`G/CC`/`G/C3`/`GM/CC`, `OHMM`/`OHM.M`, `V/V`/`DEC`/`FRAC`, `US/FT`/`US/M`).
  Every well still has GR + density + neutron + sonic + PE + caliper; 754/800
  have true deep resistivity (46 fall back to shallow/invaded for SW).
- The data is synthetic and clamped, with drilling/decoy curves mixed in.
  ~42% of wells show density rail-pinning, so **rails are a generic artifact, not
  a honeypot tell** — honeypot detection rests on *cross-curve physics
  contradictions* instead.

## Pipeline

```
LAS ingestion → curve mnemonic mapping → unit normalization → curve QC
→ VSH → PHIT → PHIE → SW → PERM → pay flag → honeypot veto
→ append-preserve LAS export → submission validation
```

The "agents" in `agents/` are the conceptual roles; each maps to a deterministic
module in `src/` (no LLM calls in the scored path — see `agents/SKILL.md`).

## Quick start

```bash
pip install -r requirements.txt          # lasio, numpy, pandas
# place the raw .las files in data/raw_las/  (unzip the evaluation archive there)
python -m src.main                        # processes all wells, writes the submission
```

Outputs land in `outputs/`:

```
outputs/
├── submission_las/            one processed .las per input well
├── submission_<date>.zip      ready-to-upload archive
├── validation_report.md       go/no-go: physics gates + round-trip checks
├── qc_reports/                qc_summary.csv, honeypot_flags.csv
└── run_logs/                  per-well methods, scores, pay, violations
```

Useful flags: `--limit N` (process first N wells), `--no-zip`,
`--roundtrip-sample N`, `--raw DIR`, `--out DIR`.

## Method summary

- **VSH** — linear gamma-ray index from robust per-well P5/P95; neutron-density
  separation fallback when GR is dead/missing.
- **PHIT** — neutron-density average (components clipped to a physical range so
  rail-pinned density can't poison it) → density-only → sonic (Wyllie) →
  regional default. Matrix density chosen from PE (sand/dolomite/limestone).
- **PHIE** — `PHIT·(1−VSH)`, enforced `0 ≤ PHIE ≤ PHIT`.
- **SW** — Simandoux (reduces to Archie in clean rock), `a=1, m=2, n=2`,
  regional `Rw` with optional temperature correction; invaded-zone resistivity
  fallback for the 46 wells lacking deep resistivity.
- **PERM** — Timur-style `log10(k)=A+B·PHIE−C·VSH`, calibrated to sane ranges.
- **PAY_FLAG** — conjunction of `VSH`, `PHIE`, `SW`, `PERM` cutoffs **and** a
  clean honeypot verdict; never a single threshold.
- **Honeypot veto** — a separate well-level suspicion score (the "physics
  auditor"); hard physics violations (negative/impossible porosity, impossible
  density-neutron separation) auto-veto the whole well to zero pay. Strict by
  design so genuine wells are not zeroed.

All physical outputs are clamped, so the physics gate passes by construction.

## Reproducibility & tuning

The run is deterministic (fixed constants, sorted well order, no randomness).
**Every tunable lives in [`src/config.py`](src/config.py)** — alias tables, unit
factors, model constants, pay cutoffs, and honeypot weights — so leaderboard
iteration only edits one file. See `agents/workflow.md` for the tuning loop.

## Output format guarantee

The writer is **append-preserve**: it keeps the original `~Version/~Well/~Params/
~Other` text verbatim and only inserts six curve definitions plus six columns
per data row. `validation.roundtrip_check` confirms every original data line is a
byte-exact prefix of the output — verified across all 800 wells.
