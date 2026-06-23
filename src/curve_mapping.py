"""
Curve mnemonic mapping and unit normalization.

Turns a raw, inconsistently-named LAS into a tidy dict of canonical curves
(GR, RHOB, NPHI, DT, RT, RXO, PE, CAL, BIT, ...) with values converted to a
single unit system. Both the original mnemonic and the standardized family are
recorded so nothing is silently lost.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np

from . import config


def _clean_unit(unit: Optional[str]) -> str:
    if unit is None:
        return ""
    return str(unit).strip().upper()


def unit_factor(family: str, unit: Optional[str]) -> float:
    """Multiplicative factor converting a raw value in `unit` to canonical units."""
    table = config.FAMILY_UNIT_TABLE.get(family)
    if not table:
        return 1.0
    return table.get(_clean_unit(unit), 1.0)


def select_family_curve(
    available: Dict[str, np.ndarray],
    units: Dict[str, str],
    family: str,
) -> Tuple[Optional[str], Optional[np.ndarray]]:
    """
    Pick the best curve for a family from the curves present in a well.

    `available` maps UPPERCASE original mnemonic -> value array.
    Returns (chosen_original_mnemonic, converted_values) or (None, None).
    Selection walks the family's priority list and takes the first mnemonic that
    is present AND has at least some valid (non-null, finite) data.
    """
    aliases = config.FAMILY_ALIASES.get(family, [])
    for alias in aliases:
        if alias in available:
            arr = available[alias]
            if arr is None:
                continue
            valid = np.isfinite(arr)
            if not valid.any():
                continue
            factor = unit_factor(family, units.get(alias))
            return alias, arr * factor
    return None, None


def _auto_fix_neutron(arr: np.ndarray) -> np.ndarray:
    """Detect porosity-unit neutron logs (0-100) that slipped past unit labels."""
    finite = arr[np.isfinite(arr)]
    if finite.size and np.nanpercentile(finite, 95) > 1.5:
        return arr / 100.0
    return arr


def build_canonical_curves(
    curves: Dict[str, np.ndarray],
    units: Dict[str, str],
) -> Dict[str, dict]:
    """
    Build the canonical curve set for one well.

    Returns a dict keyed by family name, each value a dict:
        {"source": original_mnemonic, "values": np.ndarray (canonical units)}
    Only families that resolved to a usable curve are included.
    """
    available = {k.upper(): v for k, v in curves.items()}
    units = {k.upper(): v for k, v in units.items()}

    out: Dict[str, dict] = {}
    for family in config.FAMILY_ALIASES:
        src, vals = select_family_curve(available, units, family)
        if src is None:
            continue
        if family == "NPHI":
            vals = _auto_fix_neutron(vals)
        out[family] = {"source": src, "values": vals}
    return out


def apply_valid_ranges(canonical: Dict[str, dict]) -> Dict[str, dict]:
    """
    Null out physically impossible samples per family (in place-safe copy).

    This protects every downstream calculation from unit slips and decoy spikes:
    a value outside the family's plausible range becomes NaN rather than feeding
    a porosity or saturation equation.
    """
    for family, payload in canonical.items():
        rng = config.VALID_RANGES.get(family)
        if not rng:
            continue
        lo, hi = rng
        vals = payload["values"].astype(float).copy()
        bad = (vals < lo) | (vals > hi)
        vals[bad] = np.nan
        payload["values"] = vals
    return canonical
