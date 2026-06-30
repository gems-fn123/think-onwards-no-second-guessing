# External Skills & Agentic Workflows — Compact Reference

**Project:** ThinkOnward *No Second Guessing* petrophysics challenge  
**Purpose:** Summarize useful external GitHub repos, skills, and agentic-architecture guidance found during day-4/5 research.  
**Date:** 2026-06-30

---

## 1. Answer-key reference skill

### `ttracx/oil-and-gas-claude-skills` — Well Log Interpreter

**URL:** https://github.com/ttracx/oil-and-gas-claude-skills/tree/main/skills/well_log_interpreter  
**Format:** Claude SKILL.md + optional skill.py  
**Relevance:** This is the documented answer key the project already reverse-engineered. Confirms the formulas and cutoffs.

**Core recipe (matches AGENT_BRIEF §3):**

| Curve | Formula |
|---|---|
| Vsh_GR | `(GR − 20) / (120 − 20)` linear |
| PHID | `(2.65 − RHOB) / (2.65 − 1.00)` |
| PHIN | direct NPHI |
| PHIE | `(PHID + PHIN) / 2` with Vsh correction |
| Sw_Archie | `(a / (Rw × PHIE^m))^(1/n)` |
| pay_flag | `Vsh < 0.40 ∧ Sw < 0.60 ∧ PHIE > 0.06` |

**Defaults:** Archie `a=0.62, m=2.15, n=2.0`, `Rw=0.05`, matrix=2.65, fluid=1.0.  
**Output schema:** well_info, curves (mnemonic + stats), formation_tops, interpreted_zones, net_pay_summary, quality_flags.

**Takeaway for this project:** the key is *exactly* what we inferred. Replicating it does **not** win because the honeypots are designed to pass it; the winning game is the A2/A3 trade-off, not formula fidelity.

---

## 2. Official ThinkOnward resources

### `thinkonward/challenges`

**URL:** https://github.com/thinkonward/challenges  
**Contents:** Starter notebooks + winning solutions for past ThinkOnward challenges (seismic, energy, critical minerals).  
**Relevance:** No public *No Second Guessing* material yet, but the `examples/final-submission/` folder shows expected final-submission packaging (README, requirements, reproducible notebook).

### `thinkonward/geophysical-foundation-model`

**URL:** https://github.com/thinkonward/geophysical-foundation-model  
**Contents:** ElasticViT MAE pretrained on Synthoseis synthetic seismic volumes.  
**Relevance:** Not directly applicable to LAS petrophysics, but shows ThinkOnward's investment in synthetic-data foundation models.

---

## 3. Agentic-architecture guidance

### JPT/SPE — *Designing Agentic AI Systems for Subsurface Workflows* (Jan 2026)

**URL:** https://jpt.spe.org/twa/designing-agentic-ai-systems-for-subsurface-workflows-lessons-from-automating-well-log-interpretation  
**Author:** Abdulmalik Ajibade

**Five design lessons (directly applicable to this project):**

| # | Lesson | How we applied it |
|---|---|---|
| 1 | **Prompts are not control systems.** Architectural gates must enforce termination and execution order. | `src/main.py` deterministic pipeline + validation READY gate; agent only picks levers, never free-form calculation. |
| 2 | **State is not implicit.** Cache inputs/outputs so the agent does not recompute. | Per-well petrophysics cached in `PetroResult`; run logs and dashboard JSON persist state. |
| 3 | **Physics dictates order.** VSH → PHIT → PHIE → SW → PERM → PAY. | Pipeline stages in `src/main.py` follow this dependency chain. |
| 4 | **Separate calculation from communication.** Tools return structured data; agent synthesizes summaries. | Outputs are LAS columns + JSON scoreboard + markdown reports; prose is generated from structured data. |
| 5 | **Autonomy requires justification.** Use a spectrum: deterministic for calculations, agentic for interpretation/planning. | We gave the agent autonomy only over *which single-variable probe to run next*, never over the petrophysics. |

**Bottom line:** the most robust architecture is a **hybrid deterministic pipeline + agent-driven orchestrator**. This is what this repo already does.

---

## 4. Reusable skill repos

| Repo | What it offers | Reusable for this challenge? |
|---|---|---|
| `SteadfastAsArt/geoscience-skills` | 30 geoscience skills (seismic, well logs, modelling, inversion, geostatistics) for Claude/Cursor/Copilot. | **Yes** — well-log skill could be adapted as a future agent persona; provides mnemonic normalization patterns. |
| `petro-mcp` (PyPI) | MCP server exposing `read_las`, `get_curves`, `fit_decline`, PVT, nodal analysis. | **Partially** — `read_las` / `get_curves` tooling could be reused, but challenge is deterministic, not LLM-tool-calling. |
| `zainab-iyiola/PetroLog` | Streamlit LAS interpreter: VSH methods, Archie SW, pay cutoffs, clustering, cross-plots. | **Yes** — good reference for alternate VSH estimators and pay-cutoff visualisation. |
| `adldi07/LAS-Analyzer` | Full-stack LAS platform with Claude 3.5 Sonnet integration, metadata indexing, Plotly visualizer. | **Low** — over-engineered for batch scoring; chatbot angle not useful here. |
| `venkatchittoor/offset-well-intelligence-crew` | Multi-agent crew for offset-well log analysis (Claude + Databricks, Bronze/Silver/Gold). | **Medium** — log-QC agent and formation-tops agent patterns could inspire future diagnostic tooling. |
| `marcosjacinto/petrophysics-xai-mlops` | SPWLA sonic-prediction contest with MLflow + XAI. | **Low** — data-driven target prediction, not applicable to this unsupervised physics task. |

---

## 5. Research frontier

### GeoMind — *Agentic Workflow for Lithology Classification* (arXiv 2026)

**URL:** https://arxiv.org/html/2604.21501  
**Architecture:** Planner → Executor → Reflector  
**Modules:** perception (raw logs → semantic trends), reasoning (hypotheses), analysis (validators + stratigraphic constraints).  
**Relevance:** If future work needs lithology-aware anomaly detection, this modular design is a template.

---

## 6. Compact recommendations for future agent work

1. **Reuse the ttracx SKILL.md structure** for any new agent persona: triggers, inputs, outputs, schema, quality flags.
2. **Keep the hybrid architecture** from JPT/SPE: deterministic physics pipeline + agentic orchestrator for probe selection.
3. **Do not give the agent control over petrophysical calculations** — only over which config/probe to run next.
4. **Use `SteadfastAsArt/geoscience-skills`** as a source of mnemonic-normalization and curve-QC patterns if the project expands to other LAS datasets.
5. **Avoid full-stack/chatbot approaches** (LAS-Analyzer style) for batch scoring — they add latency and fragility.

---

*Compacted from web searches on 2026-06-30. Sources cited inline.*
