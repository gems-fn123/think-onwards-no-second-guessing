"""
Petrophysical calculations: VSH, PHIT, PHIE, SW, PERM.

Design rules:
  * Every output is computed where inputs exist and left NaN (-> NULL on write)
    elsewhere. NaN in the null intervals of a log is correct, not a defect.
  * Robust fallbacks: density -> neutron-density -> sonic -> regional default.
  * Everything is clamped to physical ranges, so the physics gate passes by
    construction. Pre-clamp quantities are kept as diagnostics so the honeypot
    detector can see contradictions the clamp would otherwise hide.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np

from . import config
from .ingest import WellRecord
from .qc import QCResult


@dataclass
class PetroResult:
    vsh: np.ndarray
    phit: np.ndarray
    phie: np.ndarray
    sw: np.ndarray
    perm: np.ndarray
    methods: Dict[str, str] = field(default_factory=dict)
    diagnostics: Dict[str, float] = field(default_factory=dict)
    # pre-clamp arrays kept for the honeypot auditor
    phit_raw: Optional[np.ndarray] = None
    phie_raw: Optional[np.ndarray] = None


def _pct(arr: np.ndarray, q: float) -> float:
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return np.nan
    return float(np.nanpercentile(finite, q))


# ---------------------------------------------------------------------------
# VSH
# ---------------------------------------------------------------------------
def _vsh_neutron_density(canonical: Dict[str, dict]) -> Optional[np.ndarray]:
    """VSH from neutron-density separation, used when GR is unusable."""
    if "RHOB" not in canonical or "NPHI" not in canonical:
        return None
    rho_ma = _matrix_density(canonical)
    rhob = canonical["RHOB"]["values"]
    nphi = canonical["NPHI"]["values"]
    lo, hi = config.ND_COMPONENT_CLIP
    phid = np.clip((rho_ma - rhob) / (rho_ma - config.RHO_FLUID), lo, hi)
    nphi_c = np.clip(nphi, lo, hi)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        vsh = (nphi_c - phid) / config.VSH_ND_SHALE_SEP
    return np.clip(vsh, 0.0, 1.0)


def compute_vsh(canonical: Dict[str, dict]) -> tuple[np.ndarray, str]:
    gr = canonical["GR"]["values"] if "GR" in canonical else None
    if gr is not None:
        gr_clean = _pct(gr, 5.0)
        gr_shale = _pct(gr, 95.0)
        if np.isfinite(gr_clean) and np.isfinite(gr_shale) and gr_shale - gr_clean >= 1e-6:
            return np.clip((gr - gr_clean) / (gr_shale - gr_clean), 0.0, 1.0), "gr_linear"

    # GR missing or degenerate (dead/constant): neutron-density separation fallback.
    vsh_nd = _vsh_neutron_density(canonical)
    if vsh_nd is not None and np.isfinite(vsh_nd).any():
        return vsh_nd, "neutron_density"

    # Last resort: a neutral shale estimate wherever any porosity source has data,
    # so VSH is defined (never all-NaN) but does not assume clean sand.
    for fam in ("RHOB", "NPHI", "DT"):
        if fam in canonical:
            base = canonical[fam]["values"]
            return np.where(np.isfinite(base), 0.5, np.nan), "neutral_default"
    return None, "none"


# ---------------------------------------------------------------------------
# Matrix density from PE
# ---------------------------------------------------------------------------
def _matrix_density(canonical: Dict[str, dict]) -> float:
    if "PE" not in canonical:
        return config.RHO_MA_DEFAULT
    pe_med = _pct(canonical["PE"]["values"], 50.0)
    if not np.isfinite(pe_med):
        return config.RHO_MA_DEFAULT
    if pe_med < config.PE_SAND_MAX:
        return config.RHO_MA_SANDSTONE
    if pe_med < config.PE_DOLO_MAX:
        return config.RHO_MA_DOLOMITE
    return config.RHO_MA_LIMESTONE


# ---------------------------------------------------------------------------
# PHIT (total porosity) with fallback hierarchy
# ---------------------------------------------------------------------------
def compute_phit(canonical: Dict[str, dict]) -> tuple[np.ndarray, np.ndarray, str, float, float]:
    rho_ma = _matrix_density(canonical)
    phid = nphi = phis = None

    if "RHOB" in canonical:
        rhob = canonical["RHOB"]["values"]
        phid = (rho_ma - rhob) / (rho_ma - config.RHO_FLUID)
    if "NPHI" in canonical:
        nphi = canonical["NPHI"]["values"]
    if "DT" in canonical:
        dt = canonical["DT"]["values"]
        phis = (dt - config.DT_MATRIX) / (config.DT_FLUID - config.DT_MATRIX) / config.WYLLIE_COMPACTION

    # Honeypot diagnostic: strongly negative density porosity = density above matrix
    # (heavy-mineral spikes or rail-pinned garbage). Measured BEFORE clipping.
    neg_density_frac = 0.0
    if phid is not None:
        finite = np.isfinite(phid)
        if finite.any():
            neg_density_frac = float(np.mean(phid[finite] < -0.05))

    lo, hi = config.ND_COMPONENT_CLIP

    def _clip(a):
        return None if a is None else np.clip(a, lo, hi)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        comps = [c for c in (_clip(phid), _clip(nphi)) if c is not None]
        if comps:
            raw = np.nanmean(np.vstack(comps), axis=0)
            method = "neutron_density" if len(comps) == 2 else ("density" if phid is not None else "neutron")
        elif phis is not None:
            raw = _clip(phis)
            method = "sonic"
        else:
            any_curve = next(iter(canonical.values()))["values"]
            raw = np.full_like(any_curve, 0.12, dtype=float)
            method = "default"

    phit_raw = np.asarray(raw, dtype=float)
    phit = np.clip(phit_raw, 0.0, config.PHIT_MAX)
    return phit, phit_raw, method, rho_ma, neg_density_frac


# ---------------------------------------------------------------------------
# PHIE
# ---------------------------------------------------------------------------
def compute_phie(phit: np.ndarray, vsh: Optional[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    if vsh is None:
        vsh_use = np.zeros_like(phit)
    else:
        vsh_use = np.nan_to_num(vsh, nan=0.0)
    phie_raw = phit * (1.0 - vsh_use)
    phie = np.clip(phie_raw, 0.0, None)
    phie = np.minimum(phie, phit)  # enforce PHIE <= PHIT
    return phie, phie_raw


# ---------------------------------------------------------------------------
# SW (Archie / Simandoux)
# ---------------------------------------------------------------------------
def _rw(canonical: Dict[str, dict], n_rows: int) -> np.ndarray:
    rw = np.full(n_rows, config.RW_DEFAULT, dtype=float)
    if "TEMP" in canonical:
        temp = canonical["TEMP"]["values"]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            # Arps temperature correction (deg F).
            rw = config.RW_DEFAULT * (config.RW_TEMP_REF + 6.77) / (temp + 6.77)
        rw[~np.isfinite(rw)] = config.RW_DEFAULT
    return rw


def compute_sw(
    canonical: Dict[str, dict],
    phie: np.ndarray,
    vsh: Optional[np.ndarray],
) -> tuple[np.ndarray, str]:
    rt_source = "RT" if "RT" in canonical else ("RXO" if "RXO" in canonical else None)
    if rt_source is None:
        # No resistivity at all: cannot compute SW. Wet where porosity exists,
        # NULL where there is no data (so SW mirrors the porosity null pattern).
        return np.where(np.isfinite(phie), 1.0, np.nan), "no_resistivity_wet"

    rt = canonical[rt_source]["values"]
    rw = _rw(canonical, phie.shape[0])
    a, m, n = config.ARCHIE_A, config.ARCHIE_M, config.ARCHIE_N
    vsh_use = np.zeros_like(phie) if vsh is None else np.nan_to_num(vsh, nan=0.0)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        phie_eff = np.where(phie > 1e-4, phie, np.nan)
        if config.USE_SIMANDOUX:
            # Simandoux quadratic (reduces to Archie when VSH=0), n=2 form:
            #   C*Sw^2 + B*Sw - 1/Rt = 0
            C = np.power(phie_eff, m) / (a * rw)
            B = vsh_use / config.RSH_DEFAULT
            inv_rt = 1.0 / rt
            disc = np.square(B) + 4.0 * C * inv_rt
            sw = (-B + np.sqrt(disc)) / (2.0 * C)
            method = f"simandoux_{rt_source.lower()}"
        else:
            sw = np.power((a * rw) / (np.power(phie_eff, m) * rt), 1.0 / n)
            method = f"archie_{rt_source.lower()}"

    sw = np.clip(sw, 0.0, 1.0)
    # Porosity present but ~zero -> wet (safe, non-pay). No porosity data -> leave
    # NULL so SW matches the null pattern of the porosity curves.
    sw = np.where(np.isfinite(sw), sw, 1.0)
    sw = np.where(np.isfinite(phie), sw, np.nan)
    if rt_source == "RXO":
        method += "_fallback"
    return sw, method


# ---------------------------------------------------------------------------
# PERM (Timur-style)
# ---------------------------------------------------------------------------
def compute_perm(phie: np.ndarray, vsh: Optional[np.ndarray]) -> np.ndarray:
    vsh_use = np.zeros_like(phie) if vsh is None else np.nan_to_num(vsh, nan=0.0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        log_k = config.PERM_A + config.PERM_B * phie - config.PERM_C * vsh_use
        perm = np.power(10.0, log_k)
    perm = np.clip(perm, config.PERM_MIN, config.PERM_MAX)
    # NULL where porosity is missing, so PERM mirrors the porosity null pattern.
    perm = np.where(np.isfinite(phie), perm, np.nan)
    return perm


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def compute_all(rec: WellRecord, qc: QCResult) -> PetroResult:
    canonical = rec.canonical
    n = rec.n_rows

    vsh, vsh_method = compute_vsh(canonical)
    if vsh is None:
        vsh = np.full(n, np.nan)
        vsh_method = "none"

    phit, phit_raw, phit_method, rho_ma, neg_density_frac = compute_phit(canonical)
    phie, phie_raw = compute_phie(phit, vsh)
    sw, sw_method = compute_sw(canonical, phie, vsh)
    perm = compute_perm(phie, vsh)

    # Diagnostics for the honeypot auditor.
    valid = np.isfinite(phit_raw)

    diagnostics = {
        "rho_ma": rho_ma,
        "neg_porosity_fraction": neg_density_frac,
        "n_valid_phit": int(valid.sum()),
    }
    methods = {
        "vsh": vsh_method,
        "phit": phit_method,
        "sw": sw_method,
    }

    return PetroResult(
        vsh=vsh,
        phit=phit,
        phie=phie,
        sw=sw,
        perm=perm,
        methods=methods,
        diagnostics=diagnostics,
        phit_raw=phit_raw,
        phie_raw=phie_raw,
    )
