# Exploration Findings — ThinkOnward "No Second Guessing" Petrophysics Agent

**Project root:** `/home/gems-fn123/think-onwards-no-second-guessing`  
**Date:** 2026-06-27  
**Branch:** `day-3-and-4`  
**Authoritative plan:** `outputs/plans/day_3_4_5_plan.md`

---

## 1. .md Files Inventory

| Path | Size | 1-line Purpose |
|------|------|----------------|
| `/home/gems-fn123/think-onwards-no-second-guessing/README.md` | ~6.5 KB | Project overview: physics-first pipeline, 6 output curves, geometric-mean scoring, quickstart |
| `/home/gems-fn123/think-onwards-no-second-guessing/DECISION_QUALITY.md` | ~12 KB | Methodology for submission budget allocation; axis leverage math; diagnostic findings (Rw, A4, A3 precision cap); pre-registered experiment ladder |
| `/home/gems-fn123/think-onwards-no-second-guessing/SUBMISSIONS.md` | ~28 KB | Full submission log with scores, hypotheses, axis isolation via ratio identity, factorial plan for match-key alignment, A4 probes, daily 5-submission protocol |
| `/home/gems-fn123/think-onwards-no-second-guessing/agents/SKILL.md` | ~3 KB | Agent role definitions (8 modules), hand-off contracts, non-negotiable physics invariants, risk posture |
| `/home/gems-fn123/think-onwards-no-second-guessing/agents/workflow.md` | ~2.5 KB | End-to-end stages, build order, tuning loop with guardrails, diagnostics to watch |
| `/home/gems-fn123/think-onwards-no-second-guessing/outputs/validation_report.md` | 366 B | Latest run verdict: 800/800 wells, 0 physics-gate failures, 0 round-trip failures, **READY** |
| `/home/gems-fn123/think-onwards-no-second-guessing/.github/agents/petrophysics-tuner.agent.md` | ~4 KB | VS Code agent spec: single-variable workflow, pre-registration rules, decouple calibration from pay, match-key tie-break |
| `/home/gems-fn123/think-onwards-no-second-guessing/.kimchi/agents/petrophysics-optimizer.md` | ~17.5 KB | **Current custom agent v2** — score-maximizing optimizer with day-3/4/5 plan, strategic moves, and slot-by-slot workflow |
| `/home/gems-fn123/think-onwards-no-second-guessing/outputs/plans/day_3_4_5_plan.md` | ~13 KB | **Plan of record** — 15 submission slots across day-3 (precision vs pay-presence), day-4 (A4 hunt), day-5 (terminal branches) |
| `/home/gems-fn123/think-onwards-no-second-guessing/outputs/experiments/_template.md` | ~1.5 KB | Pre-registration template per submission |
| `/home/gems-fn123/think-onwards-no-second-guessing/outputs/experiments/PREC_400_sw035.md` | ~2.2 KB | Pre-registered experiment: day-3 slot 1 |
| `/home/gems-fn123/think-onwards-no-second-guessing/outputs/experiments/PREC_500_sw030.md` | ~2.3 KB | Pre-registered experiment: day-3 slot 2 |

---

## 2. Agent Configs

| Path | Role | Key Behavior |
|------|------|--------------|
| `agents/petrophysics_agent.yaml` | Declarative agent spec | Documents all model assumptions (VSH linear GR index, PHIT hierarchy, Simandoux SW, Timur PERM, conjunction pay, honeypot veto threshold 3.0). Mirrors `src/config.py`. |
| `agents/SKILL.md` | Module map & invariants | 8 deterministic modules (ingest → curve_map → QC → petrophysics → apparent pay → honeypot audit → final pay → LAS write → validation). Physics gate invariants: all 6 curves present, PAY_FLAG ∈ {0,1}, 0≤VSH,PHIT,PHIE,SW≤1, PHIE≤PHIT, PERM≥0, append-preserve round-trip. |
| `agents/workflow.md` | Tuning loop protocol | All knobs in `src/config.py`. Change one group at a time. Guardrails: never submit non-READY validation; small steps; strict honeypot veto to protect pay axis. |
| `.github/agents/petrophysics-tuner.agent.md` | VS Code agent instructions | Single-variable submissions ONLY; pre-register hypothesis/axis/acceptance; decouple calibration from pay (freeze PAY_FLAG to measure A4); match-key tie-break; never submit broken code. |
| `.kimchi/agents/petrophysics-optimizer.md` | **Primary custom agent** | Score-maximizing competition tuner. Follows `day_3_4_5_plan.md`. Pre-registers every experiment, changes one variable, validates READY, updates scoreboard. Knows current best 34.52, leader 39.0, three strategic moves (A/B/C), and day-5 terminal discipline. |
| `~/.kimchi/agents/` | — | Does not exist globally (only `ferments/` present) |
| `.kimchi/agents/` | — | Contains `petrophysics-optimizer.md` (custom agent) |

---

## 3. Tunables in `src/config.py` (Grouped by Axis)

### A1 — Physics Gate (must never fail; hard constraints)
- `VALID_RANGES` — per-family physical plausibility bounds (line ~140); values outside → NaN during QC
- `HARD_BOUNDS` (line ~310) — hard physics limits for honeypot OOB detection (wider than QC ranges)
- `NULL_VALUE = -999.25` (line ~64) — universal null sentinel
- `FORCE_SANDSTONE_MATRIX = True` (line ~165) — clastic section assumption; prevents dolomite matrix inflation on 185 wells
- Clamping: `PHIT_MAX=0.45`, `PHIE_MAX=0.45`, `PERM_MIN=0.0`, `PERM_MAX=20000.0`

### A2 — Pay Accuracy (active footage knob)
| Parameter | Value | Notes |
|-----------|-------|-------|
| `PAY_VSH_MAX` | 0.40 | Matches documented key |
| `PAY_PHIE_MIN` | 0.06 | Standard clastic cutoff; key uses same |
| `PAY_SW_MAX` | **0.35** | **Tuned tighter than key's 0.60** for depth-overlap (Jaccard) optimization. Tested sw=0.30 in slot 2. |
| `PAY_PERM_MIN` | 0.10 | mD |
| `PAY_USE_PERM` | **False** | Key has NO perm cutoff; set False to match |

**Pay logic:** conjunction (all must hold) AND clean honeypot verdict. `PAY_SW_MAX` is the active footage knob (0.35 → footage ~0.059; 0.60 → ~0.16).

### A3 — Honeypot Rejection (the mega-lever, squared scoring)
| Parameter | Value | Notes |
|-----------|-------|-------|
| `HONEYPOT_SCORE_THRESHOLD` | 3.0 | Hard violations weighted at threshold (auto-veto) |
| `HONEYPOT_TARGET_COUNT` | **400** | **Baseline on `day-3-and-4` branch** after day-2 precision features merged. Override via CLI `--honeypot_target N`. A3 = 100×(caught/200)² |
| `HONEYPOT_FLAG_WEIGHTS` (line ~280) | Tiered: hard=3.0, medium=1.5, soft=0.5 | Day-2 added 3 residual features in `src/honeypot_detector.py` |
| `HONEYPOT_OOB_FRACTION` | 0.05 | >5% samples violating HARD_BOUNDS → auto-veto |
| `PERVASIVE_FRACTION` | 0.30 | Fraction of valid samples for "pervasive" flags |
| `IMPOSSIBLE_POROSITY` | 0.55 | Raw porosity above this = impossible |

**Honeypot Flag Weights (line 282–300):**
- **Hard (3.0 = auto-veto):** `raw_oob_violations`, `neg_porosity_pervasive`, `impossible_porosity_pervasive`, `density_neutron_impossible`
- **Medium (1.5):** `dead_primary_curve`, `rt_porosity_contradiction`
- **Soft (0.5):** `fragile_resistivity_pay`, `no_resistivity`, `extreme_washout`

**Day-2 precision features** (added to `src/honeypot_detector.py`, lines ~141–204):
- Triple-porosity residual
- Pickett scatter
- GR–PHIE decoupling

**Current baseline run:** HONEYPOT_TARGET_COUNT=400; precision features merged.

### A4 — Curve Accuracy (diagnosed as SATURATED / not the binding constraint)
| Parameter | Value | Notes |
|-----------|-------|-------|
| `RW_MODE` | `"per_well"` | Data-derived Rw (Rwa-minimum estimator, p10); median ~0.14 vs old 0.05 |
| `RW_DEFAULT` | 0.05 | Fallback / reference |
| `RW_MIN` / `RW_MAX` | 0.02 / 0.60 | Clamp band for per-well estimate |
| `RW_RWA_PERCENTILE` | 10 | Percentile of Rwa in clean low-VSH zones |
| `ARCHIE_A` / `ARCHIE_M` / `ARCHIE_N` | 1.0 / 2.0 / 2.0 | Our values; key uses a=0.62, m=2.15 |
| `USE_SIMANDOUX` | True | Shaly-sand correction |
| `RSH_DEFAULT` | 2.0 | Shale resistivity for Simandoux |
| `VSH_FIXED_ENDPOINTS` | False | Key uses fixed 20/120 GAPI; we use per-well P5/P95 |
| `VSH_GR_CLEAN` / `VSH_GR_SHALE` | 20.0 / 120.0 | Fixed endpoints (if enabled) |
| `VSH_ND_SHALE_SEP` | 0.40 | Neutron-density fallback separation |
| `PERM_A` / `PERM_B` / `PERM_C` | -2.0 / 16.0 / 3.0 | Timur log-linear: log10(k) = A + B·PHIE - C·VSH |
| `ND_COMPONENT_CLIP` | (0.0, 0.60) | Clip PHID/NPHI before averaging |
| `PHIT_MAX` | 0.45 | Cap total porosity |

**Key A4 findings from SUBMISSIONS.md:**
- S1 (per-well Rw on SW only, PAY frozen): ratio⁴=0.996 → **SW is A4-neutral**
- P1 (density-only PHIE, pay/SW frozen): ratio⁴=1.005 → **PHIE is A4-neutral**
- M3 (key VSH 20/120 + Archie a=0.62/m=2.15): ratio⁴=0.983 → **key formulas hurt A4**
- **Conclusion:** A4 is suspected saturated. PERM (tol 0.5 log-decades) is the only untested candidate, probed in day-4 slot 6.

---

## 4. Current Score State

| Metric | Value |
|--------|-------|
| **Best public score** | **34.52** (submission `CONS`: hp700 + `PAY_SW_MAX=0.35`) on `main` |
| **Public leader** | **39.0** |
| **Gap to leader** | ~4.5 points (ratio⁴ ≈ 1.625 to close) |
| **Branch baseline** | `day-3-and-4` with day-2 precision features merged; `HONEYPOT_TARGET_COUNT=400`, `PAY_SW_MAX=0.35` |
| **Last 10 scored submissions** | H5(33.34), H6(34.43), CONS(34.52), DISAMBIG_ANTI(27.36), DISAMBIG_PAY(29.07), H4(31.50), H3(29.91), H2(27.91), H1(24.87), C3(24.40) |
| **Axis decomposition** | A3 (honeypot count) mega-lever drove 21→34; A2 (footage) secondary; A4 flat; A1 perfect |

**Disambiguation results (2026-06-26):**
- `H4` (normal suspicion, hp500): **31.50**
- `DISAMBIG_PAY` (veto weakest pay): **29.07** → loss
- `DISAMBIG_ANTI` (veto least suspicious): **27.36** → loss

**Interpretation:** Suspicion ranking **is effective** (anti ≪ normal). The A3 gains from H1→H6 are true honeypot recall, not blunt A2 suppression. But ranking precision is poor — need 700 flags to catch 200 true honeypots. Day-2 precision features aim to fix this.

---

## 5. Strategic Moves (from `outputs/plans/day_3_4_5_plan.md`)

| Move | What it bets | Risk | Slots |
|---|---|---|---|
| **A — Precision @ lower hp** | Day-2 precision features catch all 200 honeypots in top-300/400 slots → A3 stays ~100 while A2 recovers from hp700-suppression | medium | day-3 slots 1–4 |
| **B — A4 floor hunt** | A4 is suspected saturated but PERM scoring (tol 0.5 log-decades, widest of the 3 A4 curves) is untested | low–medium | day-4 slots 6–7 |
| **C — Pay-presence classifier** | Explicit "should-this-well-have-pay" model beats reliance on honeypot veto for A2 Jaccard | medium–high | day-3 slot 5 |

**Axis math reminder:**
```
ratio⁴ = (score / anchor)^4
34.52 → 36.0 needs ratio⁴ = 1.181
34.52 → 37.0 needs ratio⁴ = 1.318
34.52 → 39.0 needs ratio⁴ = 1.625
```

---

## 6. Methodology Rules Distilled (Numbered)

1. **Single-variable submissions only** — change exactly one logical parameter group per submission. Use `axis_ratio = (score_probe / score_anchor)^4` to attribute movement. (SKILL.md, workflow.md, petrophysics-tuner.agent.md, SUBMISSIONS.md)

2. **Pre-register every experiment** — before any code change, copy `outputs/experiments/_template.md` to `outputs/experiments/<id>.md` and fill hypothesis, target axis, expected ratio, acceptance/refutation criteria. (DECISION_QUALITY.md §2, petrophysics-tuner.agent.md, petrophysics-optimizer.md)

3. **Decouple calibration from pay to measure A4** — freeze `PAY_FLAG` to baseline while writing recalibrated curves; A4 is scored at key's true pay depths, independent of our PAY_FLAG. (DECISION_QUALITY.md §2.3, SUBMISSIONS.md S1/P1 probes)

4. **Never submit a non-READY validation** — `outputs/validation_report.md` must read **READY** (0 physics-gate failures, 0 round-trip failures). (workflow.md, petrophysics-tuner.agent.md)

5. **Match the documented answer key where mechanism is known** — key workflow uses: VSH<0.40, PHIE>0.06, SW<0.60, **no PERM cutoff**, Archie a=0.62/m=2.15, Rw=0.05, sandstone matrix. **But** this dataset has been tested: key formulas hurt A4 (M3 ratio⁴=0.983). Mechanism alignment is a tie-break, not an override. (README.md, SUBMISSIONS.md "KEY DISCOVERY", DECISION_QUALITY.md §3)

6. **Honeypot veto strictness protects the pay axis** — hard physics violations auto-veto (weight=threshold); soft signals accumulate. Geometric mean punishes near-zero pay axis harder than imperfect one. (SKILL.md "Risk posture", petrophysics_agent.yaml, config.py HONEYPOT_FLAG_WEIGHTS)

7. **Per-well Rw (Rwa-minimum) beats static Rw** — data-implied Rw median 0.14 vs default 0.05; S2 proved it. Don't revert. (DECISION_QUALITY.md §1, SUBMISSIONS.md S2)

8. **A3 = 100 × (caught/200)²** — squared recall makes honeypot count the dominant lever until saturation. Peak at hp700 with baseline detector; precision features aim to lower that count. (SUBMISSIONS.md scoreboard, DECISION_QUALITY.md §1)

9. **A4 is suspected saturated.** S1, P1, M3 all returned ratio⁴≈1.0. PERM (tol 0.5 log-decades) is the only untested candidate. (SUBMISSIONS.md "findings", DECISION_QUALITY.md §1, day_3_4_5_plan.md)

10. **Public score is a subset; private holdout decides final rank** — tie-break toward physically-conservative, mechanism-based choices; avoid threshold-fitted overfitting. (DECISION_QUALITY.md §2.4)

11. **Day-5 submits only terminal branches** — no new probes on day-5; submit only pre-registered variants of known winners plus the `FINAL_HEDGE` (private-holdout insurance). (day_3_4_5_plan.md §4)

12. **Use `--honeypot_target N` CLI flag** for hp count overrides; don't change `src/config.py` for temporary hp changes. (petrophysics-optimizer.md, src/main.py)

---

## 7. Open Levers / Hypotheses for Pushing Score Higher

| Priority | Lever | Status | Hypothesis | Risk |
|----------|-------|--------|------------|------|
| **P0** | Move A: precision features at hp=400/500 | **Active — day-3 slots 1, 2** | Day-2 residual features concentrate true honeypots in top slots; A3 holds at lower hp while A2 recovers | medium |
| **P1** | Move A reactive: tighten sw to 0.25 | Queued — day-3 slot 3 | If sw=0.30 won, sw=0.25 finds Jaccard sweet spot | medium |
| **P2** | Move A consolidation: best hp × best sw | Queued — day-3 slot 4 | Lock in day-3 high | high |
| **P3** | Move C: pay-presence classifier | Queued — day-3 slot 5 | Explicit pay-presence beats honeypot veto for A2 Jaccard | very high |
| **P4** | Move B: PERM Timur recalibration | Queued — day-4 slot 6 | PERM (tol 0.5 log-decades) might be A4 floor | medium |
| **P5** | Move B: neutron-only PHIT | Queued — day-4 slot 7 | One porosity component may match key better than average | low |
| **P6** | Move B reactive: winning A4 lever × alt hp | Queued — day-4 slot 8 | A4 gain compounds with A2 gain from lower hp | medium |
| **P7** | Day-4 consolidation | Queued — day-4 slot 9 | Reach day-4 ceiling | high |
| **P8** | HEDGE_KEYALIGNED | Queued — day-4 slot 10 | Private-holdout insurance (key formulas) | medium |
| **P9** | Day-5 terminal branches | Determined by day-3+day-4 | Re-submit winners + private hedge | — |
| Closed | VSH fixed endpoints, Archie 0.62/2.15 (except hedge), regional/per-field ML | Tested/rejected | Don't revisit outside HEDGE slot | — |

---

## 8. Suggested First Move

**Day-3 Slot 1: `PREC_400_sw035`** — already pre-registered in `outputs/experiments/PREC_400_sw035.md`:

- **Change:** Day-2 precision features active, `HONEYPOT_TARGET_COUNT=400` (override via `--honeypot_target 400`), `PAY_SW_MAX=0.35`
- **Hypothesis:** Precision features catch ~all 200 honeypots in top-400 slots.
- **Target axis:** **A3** (precision → enables lower hp)
- **Acceptance:** score > 29.91 (baseline H3 at hp400)
- **Refutation:** score ≤ 29.91 → precision features do not survive merge; pivot to Move C
- **Implementation:** `python3 -m src.main --honeypot_target 400` (no config change)
- **Expected axis ratio:** A3 ≥ 1.10 vs H3, others flat

**If accepted →** proceed to slot 2 (`PREC_500_sw030`).  
**If refuted →** skip slot 2 and jump to slot 5 (pay-presence at hp=700).

---

## 9. Files You Must Know

| Path | Purpose |
|------|---------|
| `src/config.py` | All tunables; one file, one truth. Baseline: `HONEYPOT_TARGET_COUNT=400`, `PAY_SW_MAX=0.35` |
| `src/main.py` | Pipeline entry; CLI args including `--honeypot_target` |
| `src/honeypot_detector.py` | Honeypot suspicion ranking; day-2 added residual features |
| `src/petrophysics.py` | VSH/PHIT/PHIE/SW/PERM computation |
| `src/pay_classifier.py` | PAY_FLAG conjunction; Move C modifies this |
| `src/validation.py` | Round-trip + physics-gate check |
| `outputs/validation_report.md` | MUST be READY before submit |
| `outputs/dashboard/submissions.json` | Authoritative score log |
| `outputs/plans/day_3_4_5_plan.md` | **Plan of record** — author of record for next 15 slots |
| `outputs/experiments/<id>.md` | Per-submission pre-registration; required before code change |
| `SUBMISSIONS.md` | Running submission narrative |
| `DECISION_QUALITY.md` | Methodology + axis leverage math |
| `agents/SKILL.md`, `agents/workflow.md`, `agents/petrophysics_agent.yaml` | Project-internal agent docs |
| `.kimchi/agents/petrophysics-optimizer.md` | **Primary custom agent** for score optimization |
| `.github/agents/petrophysics-tuner.agent.md` | VS Code agent spec |

---

**Report generated from:** All `.md` files, `agents/*.yaml`, `agents/*.md`, `.github/agents/*.md`, `.kimchi/agents/*.md`, `src/config.py`, `outputs/validation_report.md`, `outputs/dashboard/submissions.json`, `outputs/plans/day_3_4_5_plan.md`, `outputs/experiments/*.md`, `outputs/run_logs/run_20260626_133944.csv`.
