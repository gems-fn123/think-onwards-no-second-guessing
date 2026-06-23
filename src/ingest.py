"""
LAS ingestion.

Loads each raw LAS file twice, on purpose:
  1. via lasio  -> robust parsing of headers, curves, units, nulls -> NaN
  2. as raw text -> preserved verbatim so the writer can append columns without
                    reformatting anything the scorer might compare byte-for-byte.

A WellRecord bundles both views plus the canonical curve set.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

import lasio

from . import config, curve_mapping

# latin-1 round-trips any byte 1:1, so raw text written back is byte-identical
# to the original header/data we did not touch.
_ENCODING = "latin-1"


@dataclass
class WellRecord:
    path: str
    name: str
    depth: np.ndarray
    curves: Dict[str, np.ndarray]          # original mnemonic (UPPER) -> values (NaN nulls)
    units: Dict[str, str]                  # original mnemonic (UPPER) -> unit string
    raw_text: str                          # full original file text, verbatim
    n_rows: int
    step: float
    canonical: Dict[str, dict] = field(default_factory=dict)
    meta: Dict[str, object] = field(default_factory=dict)

    @property
    def well_id(self) -> str:
        return os.path.splitext(os.path.basename(self.path))[0]


def load_well(path: str) -> WellRecord:
    """Ingest one LAS file into a WellRecord with canonical curves attached."""
    with open(path, "r", encoding=_ENCODING) as fh:
        raw_text = fh.read()

    las = lasio.read(path, encoding=_ENCODING)

    # Depth index (first curve in every file in this dataset).
    depth = np.asarray(las.index, dtype=float)

    curves: Dict[str, np.ndarray] = {}
    units: Dict[str, str] = {}
    depth_mnem = las.curves[0].mnemonic.upper() if len(las.curves) else None
    for curve in las.curves:
        mnem = curve.mnemonic.upper()
        if mnem == depth_mnem:
            continue
        vals = np.asarray(curve.data, dtype=float)
        # lasio maps NULL -> NaN, but guard against stray exact null values.
        vals[np.isclose(vals, config.NULL_VALUE)] = np.nan
        curves[mnem] = vals
        units[mnem] = (curve.unit or "").strip()

    n_rows = len(depth)
    step = _infer_step(depth)

    rec = WellRecord(
        path=path,
        name=str(las.well.get("WELL").value) if "WELL" in las.well else "",
        depth=depth,
        curves=curves,
        units=units,
        raw_text=raw_text,
        n_rows=n_rows,
        step=step,
        meta={
            "depth_mnem": depth_mnem,
            "null": config.NULL_VALUE,
            "n_curves": len(curves),
        },
    )

    # Canonical curves + plausibility gating (unit-converted, decoy-spikes nulled).
    canonical = curve_mapping.build_canonical_curves(curves, units)
    canonical = curve_mapping.apply_valid_ranges(canonical)
    rec.canonical = canonical

    # Capture optional environmental scalars if present as curves.
    rec.meta["temp_curve"] = "TEMP" in canonical
    return rec


def _infer_step(depth: np.ndarray) -> float:
    d = depth[np.isfinite(depth)]
    if d.size < 2:
        return config.NULL_VALUE
    diffs = np.diff(d)
    diffs = diffs[np.isfinite(diffs) & (diffs != 0)]
    if diffs.size == 0:
        return config.NULL_VALUE
    return float(np.median(diffs))


def discover_wells(raw_dir: str) -> List[str]:
    """Return sorted list of .las file paths under raw_dir."""
    out = []
    for fn in os.listdir(raw_dir):
        if fn.lower().endswith(".las"):
            out.append(os.path.join(raw_dir, fn))
    return sorted(out)
