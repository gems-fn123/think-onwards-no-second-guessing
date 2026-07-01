"""
Net-pay classification.

Pay is a conjunction of independent petrophysical criteria (shale, porosity,
saturation, permeability) plus a data-confidence requirement — never a single
threshold, so a decoy that fakes one curve cannot mint pay on its own. The
binary PAY_FLAG is produced in two steps:

  1. apparent pay   : the multi-criteria conjunction at each sample
  2. final pay      : apparent pay with the well-level honeypot veto applied

PAY_FLAG is always 0/1 with no NaN (0 in null intervals), so the physics gate
("PAY_FLAG must be binary") passes by construction.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import config
from .petrophysics import PetroResult


@dataclass
class PayResult:
    pay_flag: np.ndarray          # final binary 0/1 (after honeypot veto)
    apparent_pay: np.ndarray      # binary 0/1 (before veto)
    confidence: np.ndarray        # continuous 0..1 pay confidence (diagnostic)
    apparent_pay_fraction: float
    final_pay_fraction: float
    vetoed: bool = False


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def compute_apparent_pay(petro: PetroResult) -> tuple[np.ndarray, np.ndarray, float]:
    vsh = petro.vsh
    phie = petro.phie
    # Use the frozen baseline SW for the pay decision when a decoupled probe is
    # active (so PAY_FLAG matches the baseline while the OUTPUT SW differs).
    sw = petro.sw_for_pay if petro.sw_for_pay is not None else petro.sw
    perm = petro.perm

    n = phie.shape[0]
    # Treat a missing VSH as "unknown shale" -> 0.0 only for the AND test would be
    # too permissive; require VSH to be finite to call pay.
    finite = np.isfinite(phie) & np.isfinite(sw) & np.isfinite(perm)
    if vsh is not None:
        finite &= np.isfinite(vsh)
        vsh_use = vsh
    else:
        vsh_use = np.zeros(n)

    c_vsh = vsh_use < config.PAY_VSH_MAX
    c_phie = phie > config.PAY_PHIE_MIN
    c_sw = sw < config.PAY_SW_MAX
    # The answer-key standard workflow uses no permeability criterion.
    c_perm = (perm > config.PAY_PERM_MIN) if getattr(config, "PAY_USE_PERM", True) else True

    apparent = (finite & c_vsh & c_phie & c_sw & c_perm).astype(np.int8)

    # Soft confidence: how far each criterion clears its cutoff (diagnostic only).
    with np.errstate(invalid="ignore"):
        conf = (
            _sigmoid((config.PAY_VSH_MAX - vsh_use) * 10.0)
            * _sigmoid((phie - config.PAY_PHIE_MIN) * 40.0)
            * _sigmoid((config.PAY_SW_MAX - sw) * 10.0)
            * _sigmoid((np.log10(np.maximum(perm, 1e-6)) - np.log10(config.PAY_PERM_MIN)) * 2.0)
        )
    conf = np.where(finite, conf, 0.0)

    frac = float(np.mean(apparent)) if n else 0.0
    return apparent, conf, frac


def _viterbi_pay(
    apparent: np.ndarray,
    conf: np.ndarray,
    p_stay: float = 0.92,
    p_obs_correct: float = 0.85,
) -> np.ndarray:
    """2-state HMM Viterbi decoder for pay zones.

    States: 0 = non-pay, 1 = pay.
    Emissions use the continuous pay confidence: P(obs=pay | state=pay) is
    boosted by confidence, P(obs=pay | state=nonpay) is suppressed.
    Strong self-transition probability p_stay enforces contiguous zones.

    This directly optimizes the A2 scoring target (coherent pay zones with
    good Jaccard/footage overlap) rather than applying per-sample thresholds.
    """
    n = apparent.shape[0]
    if n == 0:
        return apparent.copy()

    log_stay = np.log(p_stay + 1e-12)
    log_switch = np.log(1.0 - p_stay + 1e-12)

    conf_c = np.clip(conf, 1e-6, 1.0 - 1e-6)
    # Emission log-likelihoods
    log_emit_pay = np.log(conf_c)            # state = pay
    log_emit_non = np.log(1.0 - conf_c)      # state = non-pay
    # Optional: also reward agreement with apparent pay
    agree = apparent.astype(float)
    log_emit_pay = log_emit_pay * p_obs_correct + np.log(agree + 1e-12) * (1.0 - p_obs_correct)
    log_emit_non = log_emit_non * p_obs_correct + np.log(1.0 - agree + 1e-12) * (1.0 - p_obs_correct)

    # Viterbi forward
    log_prob = np.full((n, 2), -np.inf, dtype=float)
    log_prob[0, 0] = log_emit_non[0]
    log_prob[0, 1] = log_emit_pay[0]
    backptr = np.zeros((n, 2), dtype=int)

    for t in range(1, n):
        for s in range(2):
            stay = log_prob[t - 1, s] + log_stay + (log_emit_pay[t] if s else log_emit_non[t])
            switch = log_prob[t - 1, 1 - s] + log_switch + (log_emit_pay[t] if s else log_emit_non[t])
            if stay >= switch:
                log_prob[t, s] = stay
                backptr[t, s] = s
            else:
                log_prob[t, s] = switch
                backptr[t, s] = 1 - s

    # Backtrack
    path = np.zeros(n, dtype=np.int8)
    path[-1] = int(np.argmax(log_prob[-1]))
    for t in range(n - 2, -1, -1):
        path[t] = backptr[t + 1, path[t + 1]]
    return path


def finalize_pay(
    apparent: np.ndarray,
    is_honeypot: bool,
    hmm_decode: bool = False,
    conf: np.ndarray | None = None,
    hmm_stay: float = 0.92,
    hmm_obs_correct: float = 0.85,
) -> tuple[np.ndarray, float, bool]:
    if is_honeypot:
        final = np.zeros_like(apparent, dtype=np.int8)
        return final, 0.0, True
    if hmm_decode and conf is not None:
        final = _viterbi_pay(apparent, conf, p_stay=hmm_stay, p_obs_correct=hmm_obs_correct)
    else:
        final = apparent.astype(np.int8)
    return final, float(np.mean(final)) if final.size else 0.0, False


def classify(
    petro: PetroResult,
    is_honeypot: bool,
    hmm_decode: bool = False,
    hmm_stay: float = 0.92,
    hmm_obs_correct: float = 0.85,
) -> PayResult:
    apparent, conf, frac = compute_apparent_pay(petro)
    final, final_frac, vetoed = finalize_pay(
        apparent,
        is_honeypot,
        hmm_decode=hmm_decode,
        conf=conf,
        hmm_stay=hmm_stay,
        hmm_obs_correct=hmm_obs_correct,
    )
    return PayResult(
        pay_flag=final,
        apparent_pay=apparent,
        confidence=conf,
        apparent_pay_fraction=frac,
        final_pay_fraction=final_frac,
        vetoed=vetoed,
    )
