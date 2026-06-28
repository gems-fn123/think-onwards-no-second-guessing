# Project Memory — ThinkOnward No Second Guessing

**Updated:** 2026-06-27  
**Project:** `/home/gems-fn123/think-onwards-no-second-guessing`  
**Branch:** `day-3-and-4`

---

## Snapshot

| Item | Value |
|------|-------|
| Best public score | **34.52** (`CONS`: hp700 + `PAY_SW_MAX=0.35`) |
| Public leader | **39.0** |
| Gap | ~4.5 points; ratio⁴ ≈ 1.625 to close |
| Current branch baseline | `HONEYPOT_TARGET_COUNT=400`, `PAY_SW_MAX=0.35`, day-2 precision features merged |
| Plan of record | `outputs/plans/day_3_4_5_plan.md` |
| Active agent | `.kimchi/agents/petrophysics-optimizer.md` |

---

## What Works

1. **Per-well Rw (Rwa-minimum)** — median ~0.14 vs default 0.05; improved A2 without hurting A4 (S2).
2. **Sandstone matrix forced** — prevents A4 zero-out on ~185 wells.
3. **Honeypot count lever** — A3 is squared recall; overshooting to hp700 gave 34.52.
4. **Suspicion ranking is real** — anti-suspiction veto (27.36) performed far worse than normal (31.50).
5. **Pay cutoffs matching key** — VSH<0.40, PHIE>0.06, SW tuned to 0.35 (tighter than key's 0.60), no PERM.

---

## What Doesn't Work

1. **Key formulas hurt A4** — M3 (ARCHIE_A=0.62, M=2.15, fixed VSH 20/120) ratio⁴=0.983.
2. **A4 is saturated** — SW (S1 flat), PHIE (P1 flat), key formulas (M3 worse). Only PERM remains untested.
3. **Blunt honeypot count is near peak** — hp700 leaves only ~100 paying wells; beyond 700 A2 craters.
4. **Anti-suspicion and weakest-pay vetoes** — both scored worse than normal suspicion.

---

## Open Questions

1. Do day-2 precision features survive the branch merge and concentrate honeypots in top 400? (day-3 slot 1)
2. Does tightening `PAY_SW_MAX` to 0.30 or 0.25 improve A2 once precision is locked? (day-3 slots 2–3)
3. Does a pay-presence classifier beat the current conjunction-only pay logic? (day-3 slot 5)
4. Is PERM the hidden A4 floor? (day-4 slot 6)
5. Does neutron-only PHIT match the key better than the average? (day-4 slot 7)

---

## Next Action

Run **day-3 slot 1**: `PREC_400_sw035`
- `python3 -m src.main --honeypot_target 400`
- Acceptance: score > 29.91 (baseline H3 at hp400)
- If win → slot 2 (`PREC_500_sw030`); if lose → slot 5 (pay-presence at hp700)

---

## References

- Full findings: `.kimchi/docs/explore_findings.md`
- Optimizer agent: `.kimchi/agents/petrophysics-optimizer.md`
- VS Code agent: `.github/agents/petrophysics-tuner.agent.md`
- Plan: `outputs/plans/day_3_4_5_plan.md`
- Submission log: `SUBMISSIONS.md`
