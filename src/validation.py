"""
Validation / submission-readiness gate.

Two layers:
  * validate_curves()  - physics gates on the computed arrays (fast, every well).
  * roundtrip_check()  - confirms the append-preserve writer left the original
                         columns untouched (sampled wells).

write_report() rolls everything into outputs/validation_report.md, the go/no-go
artifact for submission.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np

from . import config

EPS = 1e-6


@dataclass
class WellValidation:
    well_id: str
    violations: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations


def validate_curves(well_id: str, curves: Dict[str, np.ndarray]) -> WellValidation:
    v = WellValidation(well_id=well_id)

    # Presence.
    for name in config.REQUIRED_OUTPUT_CURVES:
        if name not in curves or curves[name] is None:
            v.violations.append(f"missing curve {name}")
    if v.violations:
        return v

    # PAY_FLAG strictly binary, no NaN.
    pf = np.asarray(curves["PAY_FLAG"], dtype=float)
    if np.any(~np.isfinite(pf)):
        v.violations.append("PAY_FLAG contains NaN")
    uniq = set(np.unique(pf[np.isfinite(pf)]).tolist())
    if not uniq.issubset({0.0, 1.0}):
        v.violations.append(f"PAY_FLAG non-binary values present: {sorted(uniq)[:5]}")

    # Bounded fractional curves.
    for name in ("VSH", "PHIT", "PHIE", "SW"):
        arr = np.asarray(curves[name], dtype=float)
        fin = arr[np.isfinite(arr)]
        if fin.size == 0:
            v.violations.append(f"{name} is all-NaN")
            continue
        if fin.min() < -EPS or fin.max() > 1.0 + EPS:
            v.violations.append(f"{name} out of [0,1]: min={fin.min():.4f} max={fin.max():.4f}")

    # PHIE <= PHIT.
    phit = np.asarray(curves["PHIT"], dtype=float)
    phie = np.asarray(curves["PHIE"], dtype=float)
    m = np.isfinite(phit) & np.isfinite(phie)
    if m.any() and np.any(phie[m] > phit[m] + 1e-4):
        n_bad = int(np.sum(phie[m] > phit[m] + 1e-4))
        v.violations.append(f"PHIE > PHIT at {n_bad} samples")

    # PERM non-negative, not all-NaN.
    perm = np.asarray(curves["PERM"], dtype=float)
    pf2 = perm[np.isfinite(perm)]
    if pf2.size == 0:
        v.violations.append("PERM is all-NaN")
    elif pf2.min() < -EPS:
        v.violations.append(f"PERM negative: min={pf2.min():.4f}")

    return v


def roundtrip_check(raw_path: str, out_path: str) -> List[str]:
    """
    Confirm the output preserves the original file: every original data line must
    be a prefix of the corresponding output data line, and the output must have
    exactly six more curve definitions.
    """
    problems: List[str] = []

    def read_lines(p):
        with open(p, "r", encoding="latin-1") as fh:
            return [ln.rstrip("\r\n") for ln in fh.readlines()]

    raw = read_lines(raw_path)
    out = read_lines(out_path)

    def split_sections(lines):
        c = a = None
        for i, ln in enumerate(lines):
            s = ln.lstrip()
            if s.startswith("~"):
                t = s[1:2].upper()
                if t == "C" and c is None:
                    c = i
                if t == "A" and a is None:
                    a = i
        return c, a

    rc, ra = split_sections(raw)
    oc, oa = split_sections(out)
    if ra is None or oa is None:
        problems.append("missing ~ASCII section")
        return problems

    raw_data = [ln for ln in raw[ra + 1:] if ln.strip() and not ln.lstrip().startswith("~")]
    out_data = [ln for ln in out[oa + 1:] if ln.strip() and not ln.lstrip().startswith("~")]

    if len(raw_data) != len(out_data):
        problems.append(f"row count changed: raw={len(raw_data)} out={len(out_data)}")
    for i, (r, o) in enumerate(zip(raw_data, out_data)):
        if not o.startswith(r):
            problems.append(f"data row {i} not preserved as prefix")
            break

    # Curve-definition count: output should have original + 6.
    def count_curve_defs(lines, c, a):
        if c is None:
            return 0
        end = a if a is not None else len(lines)
        n = 0
        for ln in lines[c + 1:end]:
            s = ln.strip()
            if s and not s.startswith("~") and "." in s.split(":")[0]:
                n += 1
        return n

    rdefs = count_curve_defs(raw, rc, ra)
    odefs = count_curve_defs(out, oc, oa)
    if odefs != rdefs + len(config.REQUIRED_OUTPUT_CURVES):
        problems.append(f"curve-def count: raw={rdefs} out={odefs} (expected +{len(config.REQUIRED_OUTPUT_CURVES)})")

    return problems


def write_report(
    report_path: str,
    well_validations: List[WellValidation],
    roundtrip_problems: Dict[str, List[str]],
    summary: Dict[str, object],
) -> None:
    n = len(well_validations)
    failed = [w for w in well_validations if not w.ok]
    rt_failed = {k: v for k, v in roundtrip_problems.items() if v}

    lines: List[str] = []
    lines.append("# Submission Validation Report")
    lines.append("")
    lines.append(f"- Wells processed: **{n}**")
    lines.append(f"- Physics-gate failures: **{len(failed)}**")
    lines.append(f"- Round-trip (append-preserve) failures (sampled): **{len(rt_failed)}**")
    lines.append("")
    lines.append("## Run summary")
    for k, val in summary.items():
        lines.append(f"- {k}: {val}")
    lines.append("")
    verdict = "READY ✅" if (not failed and not rt_failed) else "NOT READY ❌"
    lines.append(f"## Verdict: {verdict}")
    lines.append("")
    if failed:
        lines.append("## Physics-gate failures")
        for w in failed[:50]:
            lines.append(f"- `{w.well_id}`: {'; '.join(w.violations)}")
        if len(failed) > 50:
            lines.append(f"- ... and {len(failed) - 50} more")
        lines.append("")
    if rt_failed:
        lines.append("## Round-trip failures")
        for wid, probs in list(rt_failed.items())[:50]:
            lines.append(f"- `{wid}`: {'; '.join(probs)}")
        lines.append("")

    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
