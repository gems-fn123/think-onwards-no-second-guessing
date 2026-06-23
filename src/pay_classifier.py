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
    c_perm = perm > config.PAY_PERM_MIN

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


def finalize_pay(apparent: np.ndarray, is_honeypot: bool) -> tuple[np.ndarray, float, bool]:
    if is_honeypot:
        final = np.zeros_like(apparent, dtype=np.int8)
        return final, 0.0, True
    final = apparent.astype(np.int8)
    return final, float(np.mean(final)) if final.size else 0.0, False


def classify(petro: PetroResult, is_honeypot: bool) -> PayResult:
    apparent, conf, frac = compute_apparent_pay(petro)
    final, final_frac, vetoed = finalize_pay(apparent, is_honeypot)
    return PayResult(
        pay_flag=final,
        apparent_pay=apparent,
        confidence=conf,
        apparent_pay_fraction=frac,
        final_pay_fraction=final_frac,
        vetoed=vetoed,
    )
