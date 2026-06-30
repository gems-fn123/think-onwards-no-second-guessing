"""
LAS header and file-level metadata leakage detector.

Extracts features from the raw LAS text that may distinguish synthetic
honeypot wells from real digitised logs. All features are deterministic
and based on header/parameter/ASCII formatting artifacts, not petrophysics.
"""
from __future__ import annotations

import re
import dataclasses
from typing import Dict, Set, Tuple

import numpy as np

from . import config
from .ingest import WellRecord


@dataclasses.dataclass
class MetadataFeatures:
    well_id: str

    # Header numeric
    start: float = float("nan")
    stop: float = float("nan")
    step: float = float("nan")
    depth_span: float = float("nan")
    n_rows: int = 0
    expected_rows: float = float("nan")
    row_count_mismatch: float = float("nan")
    null_value_str: str = ""
    null_is_standard: bool = True

    # Parameter section
    num_param_lines: int = 0
    param_section_bytes: int = 0
    has_other_section: bool = False
    date_format: str = ""
    date_style: str = "unknown"
    comp: str = ""
    srvc: str = ""
    well_name: str = ""
    field: str = ""
    location: str = ""

    # Curve section
    num_curves: int = 0
    primary_present: int = 0
    primary_missing: int = 5
    has_cal: bool = False
    has_bit: bool = False
    has_pe: bool = False
    has_sp: bool = False
    has_rxo: bool = False
    has_junk: bool = False

    # ASCII data patterns
    mean_decimal_places: float = float("nan")
    fraction_trailing_zeros: float = float("nan")
    fraction_unique_values: float = float("nan")

    # File-level
    file_size_bytes: int = 0
    line_ending: str = "unknown"
    num_sections: int = 0
    header_bytes: int = 0

    # Derived / cached detail dict for honeypot detector
    detail: Dict[str, float] = dataclasses.field(default_factory=dict)


# Known high-veto company/service names discovered from data analysis.
HIGH_VETO_COMPS: Set[str] = {"Specs and Mobility", "Lake Energy", "Kangaroo Ltd"}
HIGH_VETO_SRVCS: Set[str] = set()


def _parse_header_value(raw_text: str, key: str) -> str:
    """Extract the value part of a ~W header line."""
    pattern = rf"(?m)^{re.escape(key)}\.\s*([^:\n]+?)(?:\s*:\s*[^\n]*)?$"
    m = re.search(pattern, raw_text)
    if not m:
        return ""
    val = m.group(1).strip()
    val = re.split(r"\s{2,}", val)[0]
    return val.strip()


def _parse_numeric_header(raw_text: str, key: str) -> float:
    """Parse a numeric ~W header line (STRT, STOP, STEP, NULL)."""
    val = _parse_header_value(raw_text, key)
    if not val:
        return float("nan")
    num_part = val.split()[0]
    try:
        return float(num_part)
    except ValueError:
        return float("nan")


def _classify_date_style(date_str: str) -> str:
    s = (date_str or "").strip()
    if not s:
        return "missing"
    if re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}$", s):
        return "slash"
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return "dash_iso"
    if re.match(r"^\d{1,2}-[A-Za-z]{3}-\d{4}$", s):
        return "dash_dmy"
    if re.match(r"^\d{8}$", s):
        return "digits8"
    return "other"


def _detect_line_ending(raw_text: str) -> str:
    crlf = raw_text.count("\r\n")
    lf = raw_text.count("\n") - crlf
    if crlf > 0 and lf == 0:
        return "crlf"
    if lf > 0 and crlf == 0:
        return "lf"
    if crlf > 0 and lf > 0:
        return "mixed"
    return "unknown"


def _count_sections(raw_text: str) -> int:
    sections = set(re.findall(r"(?m)^~[A-Z]", raw_text))
    return len(sections)


def _extract_ascii_features(raw_text: str, max_rows: int = 2000) -> Tuple[float, float, float]:
    """Sample ASCII section and compute decimal/printing features."""
    m = re.search(r"(?m)^~A\s*\n", raw_text)
    if not m:
        return float("nan"), float("nan"), float("nan")

    ascii_text = raw_text[m.end():]
    lines = ascii_text.splitlines()

    values = []
    for line in lines:
        if line.startswith("~"):
            break
        for p in line.split():
            try:
                float(p)
                values.append(p)
            except ValueError:
                continue

    if not values:
        return float("nan"), float("nan"), float("nan")

    n = len(values)
    if n > max_rows:
        idx = np.linspace(0, n - 1, max_rows, dtype=int)
        sample = [values[i] for i in idx]
    else:
        sample = values

    decimal_places = []
    trailing_zeros = 0
    total = 0
    numeric_values = []

    for v in sample:
        if "." in v:
            dec = len(v.split(".")[1])
            decimal_places.append(dec)
            if v.endswith("00"):
                trailing_zeros += 1
        try:
            numeric_values.append(float(v))
        except ValueError:
            pass
        total += 1

    mean_dec = float(np.mean(decimal_places)) if decimal_places else float("nan")
    trail_zero_frac = trailing_zeros / total if total else float("nan")
    unique_frac = len(set(numeric_values)) / len(numeric_values) if numeric_values else float("nan")

    return mean_dec, trail_zero_frac, unique_frac


def _primary_curves_present(rec: WellRecord) -> Tuple[int, Dict[str, bool]]:
    present = {fam: fam in rec.canonical for fam in ("GR", "RHOB", "NPHI", "RT", "DT")}
    return sum(present.values()), present


def extract_metadata_features(rec: WellRecord) -> MetadataFeatures:
    raw = rec.raw_text
    start = _parse_numeric_header(raw, "STRT")
    stop = _parse_numeric_header(raw, "STOP")
    step = _parse_numeric_header(raw, "STEP")
    null_str = _parse_header_value(raw, "NULL")

    depth_span = stop - start if np.isfinite(start) and np.isfinite(stop) else float("nan")
    expected_rows = depth_span / step + 1 if np.isfinite(depth_span) and np.isfinite(step) and step != 0 else float("nan")
    row_mismatch = abs(rec.n_rows - expected_rows) if np.isfinite(expected_rows) else float("nan")

    primary_present, _ = _primary_curves_present(rec)
    all_mnems = set(rec.curves.keys())

    has_cal = any(m in all_mnems for m in config.CAL_ALIASES)
    has_bit = any(m in all_mnems for m in config.BIT_ALIASES)
    has_pe = any(m in all_mnems for m in config.PE_ALIASES)
    has_sp = any(m in all_mnems for m in config.SP_ALIASES)
    has_rxo = any(m in all_mnems for m in config.RXO_ALIASES)
    has_junk = any(m in all_mnems for m in config.JUNK_ALIASES)

    mean_dec, trail_zero_frac, unique_frac = _extract_ascii_features(raw)

    param_match = re.search(r"(?m)^~P\s*\n(.*?)(?=\n~[A-Z])", raw, re.DOTALL)
    param_lines = 0
    param_bytes = 0
    if param_match:
        param_text = param_match.group(1)
        param_lines = len([l for l in param_text.splitlines() if l.strip()])
        param_bytes = len(param_text.encode("utf-8", errors="ignore"))

    has_other = bool(re.search(r"(?m)^~O\b", raw))

    ascii_match = re.search(r"(?m)^~A\s*\n", raw)
    header_bytes = ascii_match.start() if ascii_match else len(raw.encode("utf-8", errors="ignore"))

    feat = MetadataFeatures(
        well_id=rec.well_id,
        start=start,
        stop=stop,
        step=step,
        depth_span=depth_span,
        n_rows=rec.n_rows,
        expected_rows=expected_rows,
        row_count_mismatch=row_mismatch,
        null_value_str=null_str,
        null_is_standard=null_str.strip() in ("-999.25", "-999.2500", "-999.25000", "-999.250000"),
        num_param_lines=param_lines,
        param_section_bytes=param_bytes,
        has_other_section=has_other,
        date_format=_parse_header_value(raw, "DATE"),
        date_style=_classify_date_style(_parse_header_value(raw, "DATE")),
        comp=_parse_header_value(raw, "COMP"),
        srvc=_parse_header_value(raw, "SRVC"),
        well_name=_parse_header_value(raw, "WELL"),
        field=_parse_header_value(raw, "FLD"),
        location=_parse_header_value(raw, "LOC"),
        num_curves=rec.meta.get("n_curves", len(rec.curves)),
        primary_present=primary_present,
        primary_missing=5 - primary_present,
        has_cal=has_cal,
        has_bit=has_bit,
        has_pe=has_pe,
        has_sp=has_sp,
        has_rxo=has_rxo,
        has_junk=has_junk,
        mean_decimal_places=mean_dec,
        fraction_trailing_zeros=trail_zero_frac,
        fraction_unique_values=unique_frac,
        file_size_bytes=len(raw.encode("utf-8", errors="ignore")),
        line_ending=_detect_line_ending(raw),
        num_sections=_count_sections(raw),
        header_bytes=header_bytes,
    )

    feat.detail = {
        "meta_date_other": float(feat.date_style == "other"),
        "meta_date_missing": float(feat.date_style == "missing"),
        "meta_comp_high": float(feat.comp in HIGH_VETO_COMPS),
        "meta_srvc_high": float(feat.srvc in HIGH_VETO_SRVCS),
        "meta_null_nonstandard": float(not feat.null_is_standard),
        "meta_primary_missing": float(feat.primary_missing),
        "meta_row_mismatch": float(feat.row_count_mismatch),
        "meta_mean_decimal": feat.mean_decimal_places if np.isfinite(feat.mean_decimal_places) else 0.0,
        "meta_trailing_zeros": feat.fraction_trailing_zeros if np.isfinite(feat.fraction_trailing_zeros) else 0.0,
        "meta_unique_values": feat.fraction_unique_values if np.isfinite(feat.fraction_unique_values) else 1.0,
        "meta_has_other_section": float(feat.has_other_section),
        "meta_num_curves": float(feat.num_curves),
        "meta_param_bytes": float(feat.param_section_bytes),
        "meta_has_junk": float(feat.has_junk),
        "meta_file_size_mb": feat.file_size_bytes / 1e6,
        "meta_num_sections": float(feat.num_sections),
        "meta_header_bytes_kb": feat.header_bytes / 1024.0,
    }

    return feat


def metadata_score(rec: WellRecord, weights: Dict[str, float] | None = None) -> float:
    """Return scalar metadata-leakage suspicion score."""
    if weights is None:
        weights = {
            "meta_date_other": 1.0,
            "meta_comp_high": 0.5,
            "meta_srvc_high": 0.0,
            "meta_null_nonstandard": 0.0,
            "meta_primary_missing": 0.0,
            "meta_row_mismatch": 0.0,
            "meta_mean_decimal": 0.0,
            "meta_trailing_zeros": 0.0,
            "meta_unique_values": 0.0,
            "meta_has_other_section": 0.0,
            "meta_num_curves": 0.0,
            "meta_param_bytes": 0.0,
            "meta_has_junk": 0.0,
            "meta_file_size_mb": 0.0,
            "meta_num_sections": 0.0,
            "meta_header_bytes_kb": 0.0,
        }

    feat = extract_metadata_features(rec)
    score = 0.0
    for key, w in weights.items():
        score += feat.detail.get(key, 0.0) * w
    return min(score, 3.0)
