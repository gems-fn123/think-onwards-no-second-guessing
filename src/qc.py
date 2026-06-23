"""
Quality control.

Produces a per-well QC summary used by every downstream stage and written to
outputs/qc_reports/. QC does not modify curves (curve_mapping already nulled
out-of-range samples); it *describes* the well so petrophysics can choose
methods, the honeypot detector can reason about contradictions, and the pay
classifier can gate on data confidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np

from . import config
from .ingest import WellRecord


@dataclass
class QCResult:
    well_id: str
    n_rows: int
    families_present: List[str]
    families_missing: List[str]
    nan_fraction: Dict[str, float] = field(default_factory=dict)
    dead_curves: List[str] = field(default_factory=list)
    flags: Dict[str, bool] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    washout_fraction: float = 0.0

    def has(self, family: str) -> bool:
        return family in self.families_present


PRIMARY_FAMILIES = ["GR", "RHOB", "NPHI", "DT", "RT"]


def _valid_fraction(arr: np.ndarray) -> float:
    if arr is None or arr.size == 0:
        return 0.0
    return float(np.mean(np.isfinite(arr)))


def _is_dead(arr: np.ndarray) -> bool:
    finite = arr[np.isfinite(arr)]
    if finite.size < 5:
        return True
    return float(np.std(finite)) < config.DEAD_CURVE_STD_EPS


def run_qc(rec: WellRecord) -> QCResult:
    canonical = rec.canonical
    present = sorted(canonical.keys())
    missing = [f for f in config.FAMILY_ALIASES if f not in canonical]

    nan_fraction: Dict[str, float] = {}
    dead: List[str] = []
    for family, payload in canonical.items():
        vals = payload["values"]
        nan_fraction[family] = 1.0 - _valid_fraction(vals)
        if _is_dead(vals):
            dead.append(family)

    flags: Dict[str, bool] = {}
    notes: List[str] = []

    # Depth integrity.
    d = rec.depth
    dd = np.diff(d[np.isfinite(d)])
    flags["depth_reversal"] = bool(np.any(dd <= 0)) if dd.size else True
    if flags["depth_reversal"]:
        notes.append("Non-monotonic / reversed depth detected.")

    # Primary-curve availability.
    for fam in PRIMARY_FAMILIES:
        flags[f"has_{fam}"] = fam in canonical
    flags["has_porosity_source"] = any(f in canonical for f in ("RHOB", "NPHI", "DT"))
    flags["no_resistivity"] = "RT" not in canonical and "RXO" not in canonical
    flags["no_deep_resistivity"] = "RT" not in canonical

    # Dead primary curve.
    flags["dead_primary_curve"] = any(f in dead for f in PRIMARY_FAMILIES)
    if flags["dead_primary_curve"]:
        notes.append(f"Dead/constant primary curve(s): {[f for f in dead if f in PRIMARY_FAMILIES]}")

    # Washout: caliper - bit size.
    washout_fraction = 0.0
    if "CAL" in canonical and "BIT" in canonical:
        cal = canonical["CAL"]["values"]
        bit = canonical["BIT"]["values"]
        m = np.isfinite(cal) & np.isfinite(bit)
        if m.any():
            washout = (cal[m] - bit[m]) > config.WASHOUT_DELTA_IN
            washout_fraction = float(np.mean(washout))
    flags["extreme_washout"] = washout_fraction > 0.5
    if flags["extreme_washout"]:
        notes.append(f"Borehole washed out over {washout_fraction:.0%} of valid samples.")

    # Density-neutron physical sanity: in clean rock |PHID - NPHI| should be modest.
    flags["density_neutron_impossible"] = _density_neutron_impossible(canonical)
    if flags["density_neutron_impossible"]:
        notes.append("Pervasive non-physical density-neutron separation.")

    return QCResult(
        well_id=rec.well_id,
        n_rows=rec.n_rows,
        families_present=present,
        families_missing=missing,
        nan_fraction=nan_fraction,
        dead_curves=dead,
        flags=flags,
        notes=notes,
        washout_fraction=washout_fraction,
    )


def _density_neutron_impossible(canonical: Dict[str, dict]) -> bool:
    """
    Flag wells where density porosity and neutron disagree by an impossible margin
    across most of the section (a synthetic-decoy signature, not normal gas/shale).
    """
    if "RHOB" not in canonical or "NPHI" not in canonical:
        return False
    rhob = canonical["RHOB"]["values"]
    nphi = canonical["NPHI"]["values"]
    phid = (config.RHO_MA_DEFAULT - rhob) / (config.RHO_MA_DEFAULT - config.RHO_FLUID)
    m = np.isfinite(phid) & np.isfinite(nphi)
    if m.sum() < 20:
        return False
    sep = np.abs(phid[m] - nphi[m])
    # >0.5 porosity-fraction disagreement is not physically reachable in real rock.
    return float(np.mean(sep > 0.5)) > config.PERVASIVE_FRACTION
