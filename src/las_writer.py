"""
Append-preserve LAS writer.

Rather than re-serialising via lasio (which would re-flow headers and risk a
byte mismatch against whatever the scorer compares), we edit the original file
text surgically:

  * keep ~Version / ~Well / ~Params / ~Other verbatim,
  * insert the six new curve definitions at the end of ~Curve Information,
  * append six columns to every row of the ~ASCII data section.

Everything the scorer might read as "the original well" is therefore unchanged;
only the six required curves are added.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np

from . import config
from .ingest import WellRecord


def _newline(raw_text: str) -> str:
    return "\r\n" if raw_text.count("\r\n") >= 1 else "\n"


def _curve_def_line(name: str) -> str:
    unit = config.OUTPUT_CURVE_UNITS.get(name, "")
    descr = config.OUTPUT_CURVE_DESCR.get(name, "")
    # MNEM left-justified to 8, then ".UNIT" padded, then " : description".
    return f"{name:<8}.{unit:<6}: {descr}"


def _fmt_value(name: str, v: float) -> str:
    """Format one appended value to a fixed-width, whitespace-delimited field."""
    if name == "PAY_FLAG":
        # Always binary; never NaN by construction.
        return f"{int(round(float(v))):>12d}"
    if not np.isfinite(v):
        return f"{config.NULL_TEXT:>14}"
    if name == "PERM":
        return f"{v:>14.4f}"
    return f"{v:>14.5f}"


def build_output_text(rec: WellRecord, new_curves: Dict[str, np.ndarray]) -> str:
    """Return the processed LAS text for one well."""
    nl = _newline(rec.raw_text)
    # Split without keeping endings; we re-join with the detected newline.
    lines = rec.raw_text.split("\n")
    lines = [ln.rstrip("\r") for ln in lines]
    # Drop a single trailing empty element produced by a final newline; we re-add it.
    trailing_newline = rec.raw_text.endswith("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]

    order = config.REQUIRED_OUTPUT_CURVES
    n_rows = rec.n_rows

    # --- locate sections ---
    curve_hdr = ascii_hdr = None
    for i, ln in enumerate(lines):
        s = ln.lstrip()
        if s.startswith("~"):
            tag = s[1:2].upper()
            if tag == "C" and curve_hdr is None:
                curve_hdr = i
            elif tag == "A" and ascii_hdr is None:
                ascii_hdr = i
    if curve_hdr is None or ascii_hdr is None:
        raise ValueError(f"{rec.well_id}: could not locate ~Curve or ~ASCII section")

    # End of curve section = next '~' line after the curve header.
    curve_end = ascii_hdr
    for i in range(curve_hdr + 1, len(lines)):
        if lines[i].lstrip().startswith("~"):
            curve_end = i
            break

    new_def_lines = [_curve_def_line(name) for name in order]

    # --- append columns to data rows ---
    # Pre-format the six appended columns per row.
    cols = {name: new_curves[name] for name in order}

    out: List[str] = []
    out.extend(lines[:curve_end])
    out.extend(new_def_lines)
    out.extend(lines[curve_end:ascii_hdr + 1])  # remaining header lines + ~ASCII header

    data_lines = lines[ascii_hdr + 1:]
    row = 0
    for ln in data_lines:
        if ln.strip() == "" or ln.lstrip().startswith("~") or ln.lstrip().startswith("#"):
            out.append(ln)
            continue
        if row < n_rows:
            suffix = "".join(_fmt_value(name, cols[name][row]) for name in order)
            out.append(ln + suffix)
            row += 1
        else:
            # More data rows than expected: pad with nulls to keep column count.
            suffix = "".join(
                _fmt_value(name, np.nan if name != "PAY_FLAG" else 0) for name in order
            )
            out.append(ln + suffix)

    text = nl.join(out)
    if trailing_newline:
        text += nl
    return text, row


def write_processed(rec: WellRecord, new_curves: Dict[str, np.ndarray], out_path: str) -> int:
    """Write the processed LAS to out_path. Returns the number of data rows written."""
    text, rows_written = build_output_text(rec, new_curves)
    with open(out_path, "w", encoding="latin-1", newline="") as fh:
        fh.write(text)
    return rows_written
