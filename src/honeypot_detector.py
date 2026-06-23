"""
Honeypot detection (the "physics auditor").

The dataset mixes real wells with engineered decoys. A correct workflow assigns
ZERO pay to honeypots. This module scores each well's *suspicion* independently
of the pay classifier (per the brief's "let a physics auditor veto bad pay"),
using only cross-curve physics contradictions — never the presence of clamp
rails or drilling/junk curves, which the profiling showed are generic artifacts.

The verdict is intentionally strict: we veto a whole well to zero pay only when
the weighted suspicion crosses the threshold, so genuine wells are not zeroed
(which would wreck the pay-accuracy axis under the geometric-mean scoring).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

import numpy as np

from . import config
from .ingest import WellRecord
from .petrophysics import PetroResult
from .qc import QCResult


@dataclass
class HoneypotResult:
    well_id: str
    score: float
    is_honeypot: bool
    flags: Dict[str, bool] = field(default_factory=dict)
    detail: Dict[str, float] = field(default_factory=dict)


def _pervasive(mask: np.ndarray, valid: np.ndarray) -> float:
    """Fraction of valid samples satisfying mask."""
    if valid.sum() == 0:
        return 0.0
    return float(np.mean(mask[valid]))


def detect(
    rec: WellRecord,
    qc: QCResult,
    petro: PetroResult,
    apparent_pay_fraction: float,
) -> HoneypotResult:
    canonical = rec.canonical
    flags: Dict[str, bool] = {}
    detail: Dict[str, float] = {}

    # 1. Pervasive negative porosity before clamp (density > matrix everywhere).
    neg_frac = petro.diagnostics.get("neg_porosity_fraction", 0.0)
    flags["neg_porosity_pervasive"] = neg_frac > config.PERVASIVE_FRACTION
    detail["neg_porosity_fraction"] = neg_frac

    # 2. Impossible high raw porosity (rock cannot exceed ~55% porosity).
    phit_raw = petro.phit_raw
    valid = np.isfinite(phit_raw)
    imp_frac = _pervasive(phit_raw > config.IMPOSSIBLE_POROSITY, valid)
    flags["impossible_porosity_pervasive"] = imp_frac > config.PERVASIVE_FRACTION
    detail["impossible_porosity_fraction"] = imp_frac

    # 3. Dead / constant primary curve (from QC).
    flags["dead_primary_curve"] = bool(qc.flags.get("dead_primary_curve", False))

    # 4. Pervasive non-physical density-neutron separation (from QC).
    flags["density_neutron_impossible"] = bool(qc.flags.get("density_neutron_impossible", False))

    # 5. Resistivity-porosity contradiction: very high deep resistivity coincident
    #    with very wet-looking, clean, high porosity. Abundant conductive (water-
    #    filled) porosity cannot also be extremely resistive.
    rt_contra = 0.0
    if "RT" in canonical and "NPHI" in canonical:
        rt = canonical["RT"]["values"]
        nphi = canonical["NPHI"]["values"]
        vsh = petro.vsh
        m = np.isfinite(rt) & np.isfinite(nphi) & np.isfinite(vsh)
        if m.sum() >= 20:
            contra = (rt > 100.0) & (nphi > 0.35) & (vsh < 0.30)
            rt_contra = float(np.mean(contra[m]))
    flags["rt_porosity_contradiction"] = rt_contra > config.PERVASIVE_FRACTION
    detail["rt_porosity_contradiction_fraction"] = rt_contra

    # 6. Fragile pay: the apparent pay leans on invaded-zone (RXO) resistivity used
    #    as a stand-in for true deep Rt. Pay built on that single fragile assumption.
    sw_method = petro.methods.get("sw", "")
    flags["fragile_resistivity_pay"] = ("fallback" in sw_method) and (apparent_pay_fraction > 0.02)

    # 7. No resistivity at all (mild — limits SW reliability).
    flags["no_resistivity"] = bool(qc.flags.get("no_resistivity", False))

    # 8. Extreme washout (mild).
    flags["extreme_washout"] = bool(qc.flags.get("extreme_washout", False))

    # Weighted score.
    score = 0.0
    for name, on in flags.items():
        if on:
            score += config.HONEYPOT_FLAG_WEIGHTS.get(name, 0.0)

    is_honeypot = score >= config.HONEYPOT_SCORE_THRESHOLD

    return HoneypotResult(
        well_id=rec.well_id,
        score=round(score, 3),
        is_honeypot=is_honeypot,
        flags=flags,
        detail=detail,
    )
