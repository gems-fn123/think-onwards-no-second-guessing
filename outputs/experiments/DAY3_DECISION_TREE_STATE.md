# Day-3 Decision Tree State — Mapped vs Unmapped Paths

**Updated:** 2026-06-28 after `PREC_400_sw035` scored 30.13.

---

## Correction on slot 1

`PREC_400_sw035` **was a new configuration**, but I initially misread it. The run used `PAY_SW_MAX=0.30` (working-tree config), not 0.35 as the experiment file originally stated.

| Config | Score | Notes |
|--------|------:|-------|
| `H_PRECISION_400` (day-2) | **30.13** | precision features + hp=400 + sw=0.35 |
| `PREC_400_sw035` (day-3 slot 1) | **30.13** | precision features + hp=400 + sw=**0.30** |

**Information gained:** tightening `PAY_SW_MAX` from 0.35 to 0.30 at hp=400 does **not** change the total score. The A2 gain from tighter footage is exactly offset by A2 loss from dropped pay.

---

## Fully mapped paths (configs already tested and scored)

### Day-1: baseline detector, no precision features

| id | hp target | PAY_SW_MAX | score | vs previous |
|----|-----------|------------|------:|-------------|
| iter3 | 200 | 0.55 | 21.22 | anchor |
| H1 | 250 | 0.55 | 24.87 | +3.65 |
| H2 | 300 | 0.55 | 27.91 | +3.04 |
| H3 | 400 | 0.55 | 29.91 | +2.00 |
| H4 | 500 | 0.55 | 31.50 | +1.59 |
| H5 | 600 | 0.55 | 33.34 | +1.84 |
| H6 | 700 | 0.55 | 34.43 | +1.09 |
| CONS | 700 | 0.35 | 34.52 | +0.09 |

### Day-2: precision features merged, default sw=0.35

| id | hp target | PAY_SW_MAX | score | vs day-1 same hp |
|----|-----------|------------|------:|------------------|
| H_PRECISION_400 | 400 | 0.35 | 30.13 | +0.22 |
| H_PRECISION_500 | 500 | 0.35 | 31.86 | +0.36 |
| H_PRECISION_600 | 600 | 0.35 | 33.40 | +0.06 |
| H_PRECISION_700 | 700 | 0.35 | 34.01 | **−0.42** |
| CONS_PRECISION_500 | 500 | 0.35 | 31.86 | flat vs H_PRECISION_500 |

### Day-3: precision features on `day-3-and-4` branch

| id | hp target | PAY_SW_MAX | score | notes |
|----|-----------|------------|------:|-------|
| PREC_400_sw035 | 400 | **0.30** | 30.13 | sw=0.30 vs H_PRECISION_400 sw=0.35 → A2-neutral |
| PREC_500_sw030 | 500 | **0.30** | **33.12** | big win vs H_PRECISION_500=31.86; hp=500 is winning hp |
| PREC_500_sw025 | 500 | **0.25** | _pending_ | tighter sw at hp=500 |

---

## Unmapped paths (genuinely new configs)

| id | hp target | PAY_SW_MAX | status | why it's new |
|----|-----------|------------|--------|--------------|
| PREC_500_sw030 | 500 | 0.30 | scored 33.12 | tighter sw at hp=500 beats sw=0.35 |
| **PREC_500_sw025** | 500 | **0.25** | **pending score** | tests if even tighter sw helps |
| CONS_500_sw025 | 500 | 0.25 | pre-registered | consolidation if sw=0.25 wins |
| CONS_500_sw030 | 500 | 0.30 | pre-registered | consolidation if sw=0.30 wins |
| PAY_PRESENCE_500 | 500 | — | pre-registered | architectural Move C at hp=500 |
| CONS_400_sw035 | 400 | 0.35 | pre-registered | consolidation if sw=0.35 wins at hp=400 |
| CONS_400_sw025 | 400 | 0.25 | pre-registered | consolidation if sw=0.25 wins at hp=400 |
| CONS_500_sw030 | 500 | 0.30 | pre-registered | consolidation if sw=0.30 wins at hp=500 |
| CONS_500_sw025 | 500 | 0.25 | pre-registered | consolidation if sw=0.25 wins at hp=500 |
| PAY_PRESENCE_400 | 400 | — | pre-registered | architectural Move C at hp=400 |
| PAY_PRESENCE_500 | 500 | — | pre-registered | architectural Move C at hp=500 |

---

## Decision tree after slot 2 (hp=500 won; slot 3 pending)

```
[Day-3 root: precision features merged, default sw=0.35]
            |
    ┌───────┴───────┐
    v               v
PREC_400_sw030    PREC_500_sw030 = 33.12
= 30.13           (win vs H_PRECISION_500=31.86)
(hp=400 loses)    |
                   v
            PREC_500_sw025 — PENDING
            hp=500, sw=0.25
                   |
          ┌────────┴────────┐
          v                 v
      win (>33.12)      lose (≤33.12)
          |                 |
          v                 v
      CONS_500_sw025    CONS_500_sw030
          |                 |
          └────────┬────────┘
                   v
            PAY_PRESENCE_500
            vs slot-4 consolidation
```

---

## What we still don't know

1. Does `PAY_SW_MAX=0.25` improve A2 at hp=500? (slot 3 — pending)
2. Which sw wins at hp=500: 0.30 or 0.25? (determines slot 4)
3. Does a pay-presence classifier beat the slot-4 consolidation? (slot 5)
4. Is PERM the hidden A4 floor? (day-4 slot 6)
5. Is neutron-only PHIT better than the average? (day-4 slot 7)

---

## Active config

`src/config.py`:
```python
PAY_SW_MAX = 0.25
```

`HONEYPOT_TARGET_COUNT=500` via `--honeypot-target 500`.

Current pending submission: `outputs/submission_20260628_PREC_500_sw025.zip`
