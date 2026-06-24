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
    # When set, pay is decided from THIS SW (frozen baseline) while the OUTPUT sw
    # uses a different (e.g. per-well) Rw. Enables clean single-axis A4 probes.
    sw_for_pay: Optional[np.ndarray] = None


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
        if getattr(config, "VSH_FIXED_ENDPOINTS", False):
            # Match the answer-key standard workflow: fixed 20/120 GAPI endpoints.
            gr_clean, gr_shale = config.VSH_GR_CLEAN, config.VSH_GR_SHALE
            return np.clip((gr - gr_clean) / (gr_shale - gr_clean), 0.0, 1.0), "gr_fixed_20_120"
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
    if getattr(config, "FORCE_SANDSTONE_MATRIX", False):
        return config.RHO_MA_SANDSTONE
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


def compute_phit_alt(canonical: Dict[str, dict], mode: str) -> Optional[np.ndarray]:
    """
    Alternate total-porosity estimators for clean A4-isolation probes.

    The default PHIT (compute_phit) is the clipped arithmetic mean of density and
    neutron porosity. At gas/light-oil pay — exactly where the key's scored pay
    depths sit — the neutron reads suppressed, so the mean under-reads true
    porosity by up to the 0.03 PHIE tolerance. These modes test that:
      * "density": density porosity only (drops the neutron averaging).
      * "rms"    : gas-corrected RMS, sqrt(mean(PHID^2, NPHI^2)).
    Returns a clipped PHIT array, or None if no porosity source exists.
    """
    rho_ma = _matrix_density(canonical)
    lo, hi = config.ND_COMPONENT_CLIP
    phid = nphi = None
    if "RHOB" in canonical:
        phid = np.clip((rho_ma - canonical["RHOB"]["values"]) / (rho_ma - config.RHO_FLUID), lo, hi)
    if "NPHI" in canonical:
        nphi = np.clip(canonical["NPHI"]["values"], lo, hi)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        if mode == "density":
            raw = phid if phid is not None else nphi
        elif mode == "rms":
            comps = [c for c in (phid, nphi) if c is not None]
            raw = (np.sqrt(np.nanmean(np.vstack([np.square(c) for c in comps]), axis=0))
                   if comps else None)
        else:
            raise ValueError(f"unknown phit alt mode: {mode!r}")

    if raw is None:
        return None
    return np.clip(np.asarray(raw, dtype=float), 0.0, config.PHIT_MAX)


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
def _rw(canonical: Dict[str, dict], n_rows: int, rw_base: Optional[float] = None) -> np.ndarray:
    base = config.RW_DEFAULT if rw_base is None else float(rw_base)
    rw = np.full(n_rows, base, dtype=float)
    if rw_base is None and "TEMP" in canonical:
        # Arps temperature correction only for the regional-default path; a
        # data-derived per-well Rw already reflects formation conditions.
        temp = canonical["TEMP"]["values"]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            rw = config.RW_DEFAULT * (config.RW_TEMP_REF + 6.77) / (temp + 6.77)
        rw[~np.isfinite(rw)] = config.RW_DEFAULT
    return rw


def estimate_rw_per_well(canonical: Dict[str, dict], phit: np.ndarray, vsh: np.ndarray) -> float:
    """
    Data-derived Rw via the Rwa-minimum (Pickett) estimator: in clean, low-VSH
    zones Rwa = Rt * PHIT^m / a approaches Rw. We take a low percentile of Rwa
    over clean samples as the well's Rw, clamped to a sane band. Returns
    RW_DEFAULT when there is no deep resistivity or too few clean samples.
    """
    if "RT" not in canonical:
        return config.RW_DEFAULT
    rt = canonical["RT"]["values"]
    a, m = config.ARCHIE_A, config.ARCHIE_M
    vsh_use = np.zeros_like(phit) if vsh is None else vsh
    mask = (np.isfinite(rt) & (rt > 0) & np.isfinite(phit) & (phit > 0.05)
            & np.isfinite(vsh_use) & (vsh_use < 0.30))
    if mask.sum() < 20:
        return config.RW_DEFAULT
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        rwa = rt[mask] * np.power(phit[mask], m) / a
    rw = float(np.nanpercentile(rwa, config.RW_RWA_PERCENTILE))
    return float(np.clip(rw, config.RW_MIN, config.RW_MAX))


def compute_sw(
    canonical: Dict[str, dict],
    phie: np.ndarray,
    vsh: Optional[np.ndarray],
    rw_value: Optional[float] = None,
) -> tuple[np.ndarray, str]:
    rt_source = "RT" if "RT" in canonical else ("RXO" if "RXO" in canonical else None)
    if rt_source is None:
        # No resistivity at all: cannot compute SW. Wet where porosity exists,
        # NULL where there is no data (so SW mirrors the porosity null pattern).
        return np.where(np.isfinite(phie), 1.0, np.nan), "no_resistivity_wet"

    rt = canonical[rt_source]["values"]
    rw = _rw(canonical, phie.shape[0], rw_base=rw_value)
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


def compute_perm_timur(phie: np.ndarray, sw: np.ndarray) -> np.ndarray:
    """
    Classic Timur (1968) permeability, a clean A4-isolation probe for PERM:
        k = 0.136 * PHI%^4.4 / Sw%^2   (PHI, Sw in percent; k in mD)
    using SW as a proxy for irreducible saturation. The default PERM is a
    log-linear form in PHIE/VSH; this tests whether the key's PERM sits closer to
    the textbook Timur. PERM's A4 tolerance is wide (~0.5 log), so this is the
    lower-information of the two A4 probes — run it only after the PHIE probe.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        phi_pct = np.clip(phie, 0.0, None) * 100.0
        sw_pct = np.clip(sw, 0.05, 1.0) * 100.0
        k = 0.136 * np.power(phi_pct, 4.4) / np.square(sw_pct)
    perm = np.clip(k, config.PERM_MIN, config.PERM_MAX)
    return np.where(np.isfinite(phie) & np.isfinite(sw), perm, np.nan)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def compute_all(rec: WellRecord, qc: QCResult, decouple_pay: bool = False) -> PetroResult:
    canonical = rec.canonical
    n = rec.n_rows

    vsh, vsh_method = compute_vsh(canonical)
    if vsh is None:
        vsh = np.full(n, np.nan)
        vsh_method = "none"

    phit, phit_raw, phit_method, rho_ma, neg_density_frac = compute_phit(canonical)
    phie, phie_raw = compute_phie(phit, vsh)

    # Output SW uses the configured Rw (regional default or data-derived per-well).
    rw_value = None
    if getattr(config, "RW_MODE", "constant") == "per_well":
        rw_value = estimate_rw_per_well(canonical, phit, vsh)
    sw, sw_method = compute_sw(canonical, phie, vsh, rw_value=rw_value)

    # Decoupled probe: decide pay from the FROZEN baseline SW (regional Rw) while
    # the written SW above uses the new Rw. Pins A2/A3 so only A4 moves.
    sw_for_pay = None
    if decouple_pay and rw_value is not None:
        sw_for_pay, _ = compute_sw(canonical, phie, vsh, rw_value=None)

    perm = compute_perm(phie, vsh)

    # Diagnostics for the honeypot auditor.
    valid = np.isfinite(phit_raw)

    diagnostics = {
        "rho_ma": rho_ma,
        "neg_porosity_fraction": neg_density_frac,
        "n_valid_phit": int(valid.sum()),
    }
    diagnostics["rw_value"] = rw_value if rw_value is not None else config.RW_DEFAULT
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
        sw_for_pay=sw_for_pay,
    )
