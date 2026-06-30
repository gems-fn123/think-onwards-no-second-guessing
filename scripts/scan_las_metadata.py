#!/usr/bin/env python3
"""
Fast LAS metadata scanner for honeypot detection research.

Goals:
  1. Read every .las file as text only (no lasio) and extract header / curve /
     parameter-section metadata features.
  2. For each primary curve (GR, RHOB, NPHI, DT, RT), sample up to 1000 ASCII
     data rows and compute distribution-of-decimal-places + round-number-ending
     fractions.
  3. Build the hard-veto honeypot list at hp750 by calling src.main.analyze_well
     + select_honeypots directly (no zip, no LAS write).
  4. Compare feature distributions between hard-veto honeypots and the rest,
     rank features by effect size, flag any near-perfect separator.
  5. Persist everything to outputs/metadata_scan_results.json.

Run:
  python scripts/scan_las_metadata.py [--limit N] [--target 750] [--raw DIR]

Designed to complete in well under 120s on the 800-well dataset.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from statistics import mean, median, pstdev
from typing import Dict, List, Optional, Tuple

# Make src importable. ROOT = project root (one level above this scripts/ file).
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src import config  # noqa: E402
from src.main import analyze_well, select_honeypots  # noqa: E402

DEFAULT_RAW = os.path.join(ROOT, "data", "raw_las")
DEFAULT_OUT = os.path.join(ROOT, "outputs", "metadata_scan_results.json")

PRIMARY_FAMILIES = ("GR", "RHOB", "NPHI", "DT", "RT")
SECTION_NAMES = ("V", "W", "C", "P", "O", "A")  # ~V ~W ~C ~P ~O ~A

# -----------------------------------------------------------------------------
# Regex / parsing helpers
# -----------------------------------------------------------------------------
_SECTION_HEADER_RE = re.compile(r"^~([A-Za-z])", re.MULTILINE)
_CURVE_MNEMONIC_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_]*)")
_FIELD_RE = re.compile(r"^([A-Z][A-Z0-9]*)\s*\.\s*([^:]*?)\s*:", re.MULTILINE)
_NULL_TOKEN = "-999.25"  # canonical null for this dataset


def _read_text(path: str) -> Tuple[str, int, str]:
    """Return (raw_text, byte_size, line_ending_style)."""
    with open(path, "rb") as fh:
        raw_bytes = fh.read()
    size = len(raw_bytes)
    has_crlf = b"\r\n" in raw_bytes
    line_ending = "crlf" if has_crlf else "lf"
    # Decode with latin-1 so every byte round-trips (matches src.ingest).
    text = raw_bytes.decode("latin-1", errors="replace")
    return text, size, line_ending


def _section_offsets(text: str) -> Dict[str, int]:
    """Map section letter (uppercased) -> byte offset of the `~X` header."""
    out: Dict[str, int] = {}
    for m in _SECTION_HEADER_RE.finditer(text):
        out[m.group(1).upper()] = m.start()
    return out


def _slice_section(text: str, sections: Dict[str, int], name: str) -> Optional[str]:
    """Return text of section `name` (between its header and the next section)."""
    if name not in sections:
        return None
    start = sections[name]
    next_starts = [v for k, v in sections.items() if v > start]
    end = min(next_starts) if next_starts else len(text)
    return text[start:end]


def _parse_well_section(text: str) -> Dict[str, Optional[float]]:
    """Extract STRT, STOP, STEP, NULL from the well section."""
    out: Dict[str, Optional[float]] = {"strt": None, "stop": None, "step": None, "null": None}
    if text is None:
        return out
    for m in _FIELD_RE.finditer(text):
        key = m.group(1).upper()
        if key not in out:
            continue
        try:
            out[key] = float(m.group(2))
        except ValueError:
            # Sometimes the value has stray text — fall back to a tolerant grab.
            try:
                out[key] = float(m.group(2).split()[0])
            except (ValueError, IndexError):
                out[key] = None
    return out


def _parse_curves(text: str) -> List[str]:
    """Extract curve mnemonic list (UPPER) from the ~C section in declaration order."""
    if text is None:
        return []
    out: List[str] = []
    for line in text.splitlines()[1:]:  # skip section header line
        s = line.strip()
        if not s:
            continue
        if s.startswith("~"):
            break
        m = _CURVE_MNEMONIC_RE.match(line)
        if m:
            out.append(m.group(1).upper())
    return out


def _column_index_for_family(curve_list: List[str], family: str) -> Optional[int]:
    """Find the column index of the first alias of `family` in the curve list."""
    aliases = config.FAMILY_ALIASES.get(family, ())
    upper_list = [c.upper() for c in curve_list]
    for alias in aliases:
        alias_u = alias.upper()
        if alias_u in upper_list:
            return upper_list.index(alias_u)
    return None


def _ascii_lines(raw_text: str, sections: Dict[str, int], max_lines: int = 2000) -> List[str]:
    """Return up to `max_lines` non-empty ASCII data rows (whitespace-stripped)."""
    if "A" not in sections:
        return []
    body = raw_text[sections["A"]:].splitlines()[1:]  # skip the header
    rows: List[str] = []
    for line in body:
        s = line.strip()
        if not s:
            continue
        if s.startswith("~"):
            break
        rows.append(s)
        if len(rows) >= max_lines:
            break
    return rows


def _count_decimals(token: str) -> int:
    """Count digits after the decimal point in a numeric token (incl. trailing zeros)."""
    # Strip sign (so '-1.23' parses to 1.23)
    s = token.strip().lstrip("+-")
    # Handle scientific notation: count decimals of the mantissa.
    for sep in ("e", "E"):
        if sep in s:
            s = s.split(sep, 1)[0]
            break
    if "." in s:
        return len(s.split(".", 1)[1])
    return 0


def _ends_with_any(token: str, suffixes: Tuple[str, ...]) -> bool:
    """True if the numeric token's rightmost non-whitespace chars match any suffix."""
    s = token.strip()
    return any(s.endswith(suf) for suf in suffixes)


# -----------------------------------------------------------------------------
# Per-well feature record
# -----------------------------------------------------------------------------
@dataclass
class WellFeatures:
    well_id: str
    file_size: int
    line_ending: str
    strt: Optional[float]
    stop: Optional[float]
    step: Optional[float]
    null_val: Optional[float]
    depth_span: Optional[float]
    n_curves: int
    curve_list: List[str]
    sections_present: List[str]
    param_line_count: int
    param_byte_length: int
    null_is_999_25: bool
    # Per-primary ASCII statistics: median decimal places + round-ending fractions.
    primary_decimals: Dict[str, Optional[float]] = field(default_factory=dict)
    primary_ends_0: Dict[str, Optional[float]] = field(default_factory=dict)
    primary_ends_5: Dict[str, Optional[float]] = field(default_factory=dict)
    primary_ends_25: Dict[str, Optional[float]] = field(default_factory=dict)
    primary_ends_50: Dict[str, Optional[float]] = field(default_factory=dict)
    primary_ends_75: Dict[str, Optional[float]] = field(default_factory=dict)
    primary_ends_00: Dict[str, Optional[float]] = field(default_factory=dict)
    primary_n_samples: Dict[str, int] = field(default_factory=dict)


def _scan_one(path: str) -> WellFeatures:
    """Read one LAS file as text and build its feature record (no lasio)."""
    text, size, line_ending = _read_text(path)
    sections = _section_offsets(text)
    well_text = _slice_section(text, sections, "W")
    curve_text = _slice_section(text, sections, "C")
    param_text = _slice_section(text, sections, "P")
    well_fields = _parse_well_section(well_text or "")
    curve_list = _parse_curves(curve_text or "")

    strt = well_fields["strt"]
    stop = well_fields["stop"]
    step = well_fields["step"]
    null_val = well_fields["null"]
    span = (stop - strt) if (strt is not None and stop is not None) else None

    # Param section stats — exclude the header line itself.
    param_lines: List[str] = []
    if param_text:
        for line in param_text.splitlines()[1:]:
            if line.strip():
                param_lines.append(line)
    # ASCII sampling for primary curves.
    ascii_rows = _ascii_lines(text, sections, max_lines=2000)

    feats = WellFeatures(
        well_id=os.path.splitext(os.path.basename(path))[0],
        file_size=size,
        line_ending=line_ending,
        strt=strt,
        stop=stop,
        step=step,
        null_val=null_val,
        depth_span=span,
        n_curves=len(curve_list),
        curve_list=curve_list,
        sections_present=sorted(sections.keys()),
        param_line_count=len(param_lines),
        param_byte_length=len(param_text.encode("latin-1")) if param_text else 0,
        null_is_999_25=(null_val is not None and abs(null_val - (-999.25)) < 1e-6),
    )

    # Sample ~1000 rows uniformly across the ASCII section.
    if ascii_rows:
        if len(ascii_rows) <= 1000:
            sample_rows = ascii_rows
        else:
            stride = len(ascii_rows) / 1000.0
            sample_rows = [ascii_rows[int(i * stride)] for i in range(1000)]

        for fam in PRIMARY_FAMILIES:
            col_idx = _column_index_for_family(curve_list, fam)
            if col_idx is None:
                feats.primary_decimals[fam] = None
                feats.primary_ends_0[fam] = None
                feats.primary_ends_5[fam] = None
                feats.primary_ends_25[fam] = None
                feats.primary_ends_50[fam] = None
                feats.primary_ends_75[fam] = None
                feats.primary_ends_00[fam] = None
                feats.primary_n_samples[fam] = 0
                continue

            decimals: List[int] = []
            n0 = n5 = n25 = n50 = n75 = n00 = 0
            n_total = 0
            for row in sample_rows:
                parts = row.split()
                if col_idx >= len(parts):
                    continue
                tok = parts[col_idx]
                # Skip nulls (they bias decimal counts).
                if tok.strip() == _NULL_TOKEN or _ends_with_any(tok, (".25", ".25000", ".2500", ".250")):
                    # Be conservative: only skip exact "-999.25*" tokens.
                    stripped = tok.strip()
                    if stripped == "-999.25000" or stripped.startswith("-999.25"):
                        continue
                n_total += 1
                decimals.append(_count_decimals(tok))
                if tok.endswith("0"):
                    n0 += 1
                if tok.endswith("5"):
                    n5 += 1
                if tok.endswith("25"):
                    n25 += 1
                if tok.endswith("50"):
                    n50 += 1
                if tok.endswith("75"):
                    n75 += 1
                if tok.endswith("00"):
                    n00 += 1

            feats.primary_n_samples[fam] = n_total
            feats.primary_decimals[fam] = float(median(decimals)) if decimals else None
            feats.primary_ends_0[fam] = (n0 / n_total) if n_total else None
            feats.primary_ends_5[fam] = (n5 / n_total) if n_total else None
            feats.primary_ends_25[fam] = (n25 / n_total) if n_total else None
            feats.primary_ends_50[fam] = (n50 / n_total) if n_total else None
            feats.primary_ends_75[fam] = (n75 / n_total) if n_total else None
            feats.primary_ends_00[fam] = (n00 / n_total) if n_total else None

    return feats


# -----------------------------------------------------------------------------
# Comparison / effect size
# -----------------------------------------------------------------------------
def _cohens_d(g1: List[float], g2: List[float]) -> float:
    """Absolute Cohen's d; returns 0 if either group has <2 samples or zero pooled std."""
    if len(g1) < 2 or len(g2) < 2:
        return 0.0
    m1, m2 = mean(g1), mean(g2)
    s1, s2 = pstdev(g1), pstdev(g2)
    pooled = ((s1 ** 2 + s2 ** 2) / 2.0) ** 0.5
    if pooled == 0:
        return 0.0
    return abs(m1 - m2) / pooled


def _overlap_ratio(g1: List[float], g2: List[float]) -> float:
    """Fraction of group1 values that fall inside the [min, max] range of group2.
    Lower => better separation. 1.0 = fully overlapping."""
    if not g1 or not g2:
        return 1.0
    lo, hi = min(g2), max(g2)
    if hi == lo:
        return 1.0
    inside = sum(1 for v in g1 if lo <= v <= hi)
    return inside / len(g1)


def _summarise(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"n": 0, "mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "median": 0.0}
    return {
        "n": len(values),
        "mean": round(mean(values), 6),
        "std": round(pstdev(values), 6) if len(values) > 1 else 0.0,
        "min": round(min(values), 6),
        "max": round(max(values), 6),
        "median": round(median(values), 6),
    }


def _flatten_features(records: List[WellFeatures]) -> Dict[str, List[Optional[float]]]:
    """Turn each WellFeatures field into a list (None-safe) for downstream analysis."""
    n = len(records)
    out: Dict[str, List[Optional[float]]] = {
        "file_size": [r.file_size for r in records],
        "strt": [r.strt for r in records],
        "stop": [r.stop for r in records],
        "step": [r.step for r in records],
        "null_val": [r.null_val for r in records],
        "depth_span": [r.depth_span for r in records],
        "n_curves": [r.n_curves for r in records],
        "param_line_count": [r.param_line_count for r in records],
        "param_byte_length": [r.param_byte_length for r in records],
        "null_is_999_25": [1.0 if r.null_is_999_25 else 0.0 for r in records],
        "line_ending_crlf": [1.0 if r.line_ending == "crlf" else 0.0 for r in records],
        "section_count": [float(len(r.sections_present)) for r in records],
        "has_V": [1.0 if "V" in r.sections_present else 0.0 for r in records],
        "has_W": [1.0 if "W" in r.sections_present else 0.0 for r in records],
        "has_C": [1.0 if "C" in r.sections_present else 0.0 for r in records],
        "has_P": [1.0 if "P" in r.sections_present else 0.0 for r in records],
        "has_O": [1.0 if "O" in r.sections_present else 0.0 for r in records],
        "has_A": [1.0 if "A" in r.sections_present else 0.0 for r in records],
    }
    for fam in PRIMARY_FAMILIES:
        out[f"primary_{fam}_decimals"] = [r.primary_decimals.get(fam) for r in records]
        out[f"primary_{fam}_ends_0"] = [r.primary_ends_0.get(fam) for r in records]
        out[f"primary_{fam}_ends_5"] = [r.primary_ends_5.get(fam) for r in records]
        out[f"primary_{fam}_ends_25"] = [r.primary_ends_25.get(fam) for r in records]
        out[f"primary_{fam}_ends_50"] = [r.primary_ends_50.get(fam) for r in records]
        out[f"primary_{fam}_ends_75"] = [r.primary_ends_75.get(fam) for r in records]
        out[f"primary_{fam}_ends_00"] = [r.primary_ends_00.get(fam) for r in records]
        out[f"primary_{fam}_n_samples"] = [float(r.primary_n_samples.get(fam, 0)) for r in records]
    return out


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="LAS metadata scanner for honeypot research")
    ap.add_argument("--raw", default=DEFAULT_RAW, help="directory of .las files")
    ap.add_argument("--out", default=DEFAULT_OUT, help="output JSON path")
    ap.add_argument("--target", type=int, default=750, help="honeypot target for hard-veto run")
    ap.add_argument("--limit", type=int, default=0, help="cap wells scanned (0 = all)")
    args = ap.parse_args(argv)

    # 1. Discover wells.
    all_files = sorted(
        os.path.join(args.raw, f) for f in os.listdir(args.raw) if f.lower().endswith(".las")
    )
    if args.limit:
        all_files = all_files[: args.limit]
    if not all_files:
        print(f"No .las files found in {args.raw}", file=sys.stderr)
        return 2
    print(f"[scan] {len(all_files)} wells discovered in {args.raw}")

    t0 = time.time()
    # 2. Text-only feature extraction.
    records: List[WellFeatures] = []
    for i, path in enumerate(all_files, 1):
        try:
            records.append(_scan_one(path))
        except Exception as exc:
            print(f"[scan] FAILED {os.path.basename(path)}: {exc}", file=sys.stderr)
    print(f"[scan] text features done in {time.time() - t0:.1f}s ({len(records)} records)")

    # 3. Hard-veto detection via analyze_well + select_honeypots (no zip, no LAS write).
    t1 = time.time()
    runs = []
    errors = []
    for i, path in enumerate(all_files, 1):
        wid = os.path.splitext(os.path.basename(path))[0]
        try:
            runs.append(analyze_well(path))
        except Exception as exc:
            errors.append(f"{wid}: {exc}")
    honey_set, hard_set = select_honeypots(runs, target=args.target)
    # Map well_id -> is_honeypot_at_target / hard_veto
    hard_veto_map: Dict[str, bool] = {}
    flagged_map: Dict[str, bool] = {}
    for j, r in enumerate(runs):
        wid = r["rec"].well_id
        hard_veto_map[wid] = bool(r["hp"].hard_veto)
        flagged_map[wid] = j in honey_set
    print(
        f"[scan] detector run in {time.time() - t1:.1f}s: hard_veto={len(hard_set)}, "
        f"flagged_at_target={len(honey_set)} (target={args.target})"
    )
    if errors:
        print(f"[scan] detector errors: {len(errors)}", file=sys.stderr)

    # 4. Split by hard-veto status and compare distributions.
    hv_yes_idx = [j for j, r in enumerate(records) if hard_veto_map.get(r.well_id)]
    hv_no_idx = [j for j, r in enumerate(records) if not hard_veto_map.get(r.well_id)]
    flagged_yes_idx = [j for j, r in enumerate(records) if flagged_map.get(r.well_id)]
    flagged_no_idx = [j for j, r in enumerate(records) if not flagged_map.get(r.well_id)]

    flat = _flatten_features(records)
    feature_stats: Dict[str, Dict] = {}
    separators_hard: List[Dict] = []
    separators_target: List[Dict] = []

    for feat, values in flat.items():
        clean = [(j, v) for j, v in enumerate(values) if v is not None]
        if not clean:
            continue
        g_yes_h = [v for j, v in clean if j in hv_yes_idx]
        g_no_h = [v for j, v in clean if j in hv_no_idx]
        g_yes_t = [v for j, v in clean if j in flagged_yes_idx]
        g_no_t = [v for j, v in clean if j in flagged_no_idx]
        d_h = _cohens_d(g_yes_h, g_no_h)
        d_t = _cohens_d(g_yes_t, g_no_t)
        ov_h = _overlap_ratio(g_yes_h, g_no_h)
        ov_t = _overlap_ratio(g_yes_t, g_no_t)
        feature_stats[feat] = {
            "hard_veto": {
                "yes": _summarise(g_yes_h),
                "no": _summarise(g_no_h),
                "cohens_d": round(d_h, 4),
                "overlap_ratio": round(ov_h, 4),
            },
            "flagged_at_target": {
                "yes": _summarise(g_yes_t),
                "no": _summarise(g_no_t),
                "cohens_d": round(d_t, 4),
                "overlap_ratio": round(ov_t, 4),
            },
        }
        if d_h > 0.0:
            separators_hard.append({"feature": feat, "cohens_d": d_h, "overlap_ratio": ov_h})
        if d_t > 0.0:
            separators_target.append({"feature": feat, "cohens_d": d_t, "overlap_ratio": ov_t})

    separators_hard.sort(key=lambda x: x["cohens_d"], reverse=True)
    separators_target.sort(key=lambda x: x["cohens_d"], reverse=True)

    near_perfect_hard = [
        s for s in separators_hard
        if s["cohens_d"] >= 1.5 or s["overlap_ratio"] <= 0.10
    ]
    near_perfect_target = [
        s for s in separators_target
        if s["cohens_d"] >= 1.5 or s["overlap_ratio"] <= 0.10
    ]

    # 5. Build JSON payload.
    payload = {
        "meta": {
            "raw_dir": args.raw,
            "n_wells": len(records),
            "target": args.target,
            "elapsed_seconds": round(time.time() - t0, 1),
            "primary_families": list(PRIMARY_FAMILIES),
        },
        "group_counts": {
            "hard_veto_yes": len(hv_yes_idx),
            "hard_veto_no": len(hv_no_idx),
            "flagged_yes": len(flagged_yes_idx),
            "flagged_no": len(flagged_no_idx),
            "detector_errors": len(errors),
        },
        "wells": [
            {
                "well_id": r.well_id,
                "hard_veto": hard_veto_map.get(r.well_id, False),
                "flagged_at_target": flagged_map.get(r.well_id, False),
                **{k: v for k, v in asdict(r).items() if k != "well_id"},
            }
            for r in records
        ],
        "feature_stats": feature_stats,
        "top_separators_hard_veto": separators_hard[:10],
        "top_separators_flagged_at_target": separators_target[:10],
        "near_perfect_separators_hard_veto": near_perfect_hard,
        "near_perfect_separators_flagged_at_target": near_perfect_target,
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
    print(f"[scan] wrote {args.out}")

    # 6. Console report.
    print("\n=== Group counts ===")
    for k, v in payload["group_counts"].items():
        print(f"  {k}: {v}")
    print("\n=== Top 5 features separating hard-veto honeypots ===")
    for s in separators_hard[:5]:
        print(
            f"  {s['feature']:<32s} d={s['cohens_d']:.3f}  overlap={s['overlap_ratio']:.3f}"
        )
    print("\n=== Top 5 features separating flagged-at-target wells ===")
    for s in separators_target[:5]:
        print(
            f"  {s['feature']:<32s} d={s['cohens_d']:.3f}  overlap={s['overlap_ratio']:.3f}"
        )
    if near_perfect_hard:
        print("\n=== Near-perfect separators (hard veto) ===")
        for s in near_perfect_hard:
            print(f"  {s['feature']:<32s} d={s['cohens_d']:.3f}  overlap={s['overlap_ratio']:.3f}")
    if near_perfect_target:
        print("\n=== Near-perfect separators (flagged at target) ===")
        for s in near_perfect_target:
            print(f"  {s['feature']:<32s} d={s['cohens_d']:.3f}  overlap={s['overlap_ratio']:.3f}")
    print(f"\n[scan] total elapsed: {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
