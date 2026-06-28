# Custom Agent Resources — ThinkOnward No Second Guessing

This directory contains knowledge, agent instructions, and memory for AI agents working on this project inside Codespaces.

## Files

| File | Purpose |
|------|---------|
| `agents/petrophysics-optimizer.md` | **Primary score-optimizing agent** — full workflow, current state, 15-submission plan, anti-patterns. Start here for tuning. |
| `docs/explore_findings.md` | Comprehensive exploration report: project inventory, tunables by axis, current score state, methodology rules, open levers, suggested first move. |
| `MEMORY.md` | Concise project memory: what works, what doesn't, open questions, next action. |

## Other Agent Locations

- `agents/EXPLORE_FINDINGS.md` — copy of exploration findings (project-root accessible)
- `agents/SKILL.md` — module map & physics invariants
- `agents/workflow.md` — tuning loop protocol
- `agents/petrophysics_agent.yaml` — declarative config mirroring `src/config.py`
- `.github/agents/petrophysics-tuner.agent.md` — VS Code agent spec
- `.github/agents/petrophysics-optimizer.agent.md` — copy of primary optimizer agent

## Quick Start for Any Agent

1. Read `MEMORY.md` for current state.
2. Read `agents/petrophysics-optimizer.md` for full instructions.
3. Read `outputs/plans/day_3_4_5_plan.md` for the next pre-registered slot.
4. Follow the methodology rules in `docs/explore_findings.md` §6.
