# Agent Resources

This directory defines the conceptual agent roles and houses transferrable knowledge for AI agents working on this project.

## Core Agent Docs

| File | Purpose |
|------|---------|
| `SKILL.md` | Module map, hand-off contracts, physics-gate invariants, risk posture |
| `workflow.md` | End-to-end pipeline stages, tuning loop, guardrails |
| `petrophysics_agent.yaml` | Declarative agent spec mirroring `src/config.py` |
| `EXPLORE_FINDINGS.md` | Comprehensive exploration report (current state, tunables, methodology, open levers) |

## Custom Agents (Latest / Transferrable)

| Location | File | Purpose |
|----------|------|---------|
| `.kimchi/agents/` | `petrophysics-optimizer.md` | **Primary score-optimizing agent** with day-3/4/5 plan |
| `.github/agents/` | `petrophysics-tuner.agent.md` | VS Code agent spec (updated with current state) |
| `.github/agents/` | `petrophysics-optimizer.agent.md` | Copy of primary optimizer agent for GitHub/Codespaces tooling |
| `.kimchi/` | `MEMORY.md` | Concise project memory: what works, what doesn't, next action |
| `.kimchi/docs/` | `explore_findings.md` | Authoritative exploration report |

## For AI Agents

Start with `.kimchi/MEMORY.md`, then read `.kimchi/agents/petrophysics-optimizer.md` for the full operational guide.
