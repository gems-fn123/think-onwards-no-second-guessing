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

from . import config, curve_mapping
from .ingest import WellRecord
from .petrophysics import PetroResult
from .qc import QCResult


def _raw_oob_fraction(rec: WellRecord) -> float:
    """
    Fraction of depth samples where any primary RAW measurement is physically
    impossible (outside HARD_BOUNDS). Uses ungated curves so baked-in violations
    are seen. This is the cleanest honeypot signature in the dataset.
    """
    raw = curve_mapping.build_canonical_curves(rec.curves, rec.units)  # no range gating
    n = rec.n_rows
    viol = np.zeros(n)
    valid = np.zeros(n, dtype=bool)
    for fam, (lo, hi) in config.HARD_BOUNDS.items():
        if fam not in raw:
            continue
        a = raw[fam]["values"]
        m = np.isfinite(a)
        valid[m] = True
        viol[m & ((a < lo) | (a > hi))] += 1
    if not valid.any():
        return 0.0
    return float(np.mean(viol[valid] > 0))


@dataclass
class HoneypotResult:
    well_id: str
    score: float                 # weighted boolean-flag score (hard-veto logic)
    is_honeypot: bool            # hard auto-veto only; global step may add more
    suspicion: float = 0.0       # continuous rank key (hard score + severities)
    hard_veto: bool = False      # a hard physics violation fired -> always veto
    flags: Dict[str, bool] = field(default_factory=dict)
    detail: Dict[str, float] = field(default_factory=dict)


def _min_autocorr(rec: WellRecord) -> float:
    """Minimum lag-1 autocorrelation across primary curves (low = noisy/suspect)."""
    acs = []
    for fam in ("RHOB", "NPHI", "GR", "DT"):
        if fam not in rec.canonical:
            continue
        a = rec.canonical[fam]["values"]
        x = a[np.isfinite(a)]
        if x.size > 30 and np.std(x) > 1e-9:
            acs.append(float(np.corrcoef(x[:-1], x[1:])[0, 1]))
    return min(acs) if acs else 0.6


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

    # 9. Raw out-of-range physics violations (hard auto-veto). Cleanest signature:
    #    pervasively impossible raw measurements baked into the well.
    oob_frac = _raw_oob_fraction(rec)
    flags["raw_oob_violations"] = oob_frac > config.HONEYPOT_OOB_FRACTION
    detail["raw_oob_fraction"] = oob_frac

    # 10. GR-PHIE Decoupling (High GR + High Porosity)
    gr_phie_frac = 0.0
    if "GR" in canonical:
        gr = canonical["GR"]["values"]
        phie = petro.phie
        m = np.isfinite(gr) & np.isfinite(phie)
        if m.sum() > 20:
            contra = (gr > 100.0) & (phie > 0.20)
            gr_phie_frac = float(np.mean(contra[m]))
    detail["gr_phie_fraction"] = gr_phie_frac

    # 11. Pickett Scatter (Rw Variance in wet zones)
    pickett_scatter = 0.0
    if "RT" in canonical:
        rt = canonical["RT"]["values"]
        phit = petro.phit
        vsh = petro.vsh
        m = np.isfinite(rt) & np.isfinite(phit) & np.isfinite(vsh) & (phit > 0.05)
        if m.sum() > 20:
            rwa = rt[m] * (phit[m] ** config.ARCHIE_M)
            clean_m = vsh[m] < 0.30
            if clean_m.sum() > 20:
                rwa_clean = rwa[clean_m]
                rwa_clean = rwa_clean[(rwa_clean > 0.001) & (rwa_clean < 10.0)]
                if rwa_clean.size > 20:
                    pickett_scatter = float(np.std(np.log10(rwa_clean)))
    detail["pickett_scatter"] = pickett_scatter

    # 12. Triple-Porosity Variance
    por_variance = 0.0
    if "RHOB" in canonical and "NPHI" in canonical and "DT" in canonical:
        rhob = canonical["RHOB"]["values"]
        nphi = canonical["NPHI"]["values"]
        dt = canonical["DT"]["values"]
        m = np.isfinite(rhob) & np.isfinite(nphi) & np.isfinite(dt)
        if m.sum() > 20:
            phid = (2.65 - rhob[m]) / (2.65 - 1.0)
            phin = nphi[m]
            phis = (dt[m] - 55.5) / (189.0 - 55.5)
            pors = np.vstack([phid, phin, phis])
            var_per_depth = np.var(pors, axis=0)
            por_variance = float(np.mean(var_per_depth))
    detail["por_variance"] = por_variance

    # Weighted boolean score -> hard auto-veto.
    score = 0.0
    for name, on in flags.items():
        if on:
            score += config.HONEYPOT_FLAG_WEIGHTS.get(name, 0.0)
    hard_veto = score >= config.HONEYPOT_SCORE_THRESHOLD

    # Continuous suspicion = boolean score + graded severities. Lets the global
    # ranking step order the soft band (wells with no hard violation) so we can
    # fill up to the known 25% honeypot base rate by suspicion, worst-first.
    min_ac = _min_autocorr(rec)
    detail["min_autocorr"] = min_ac
    severity = (
        2.0 * detail.get("raw_oob_fraction", 0.0)
        + 2.0 * neg_frac
        + 2.0 * imp_frac
        + 1.0 * detail.get("rt_porosity_contradiction_fraction", 0.0)
        + 2.0 * gr_phie_frac                     # New: GR-PHIE contradiction
        + 1.0 * min(pickett_scatter, 1.0)        # New: Pickett scatter
        + 10.0 * por_variance                    # New: Triple-porosity variance
        + 1.0 * max(0.0, 0.60 - min_ac)          # noisy/discontinuous curves
        + 0.5 * qc.washout_fraction
    )
    suspicion = score + severity

    return HoneypotResult(
        well_id=rec.well_id,
        score=round(score, 3),
        is_honeypot=hard_veto,
        suspicion=round(suspicion, 4),
        hard_veto=hard_veto,
        flags=flags,
        detail=detail,
    )
