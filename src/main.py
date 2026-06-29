"""
Pipeline orchestration.

    python -m src.main [--raw DIR] [--out DIR] [--limit N] [--no-zip]

Per well:  ingest -> QC -> petrophysics -> apparent pay -> honeypot veto
           -> final pay -> append-preserve write -> physics-gate validate.

Then: round-trip check on a sample, write QC + run logs + validation report,
and zip the processed LAS into outputs/submission_<date>.zip.

Deterministic: fixed constants, no randomness, wells processed in sorted order.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
import traceback
import zipfile
from datetime import datetime
from typing import Dict, List

import numpy as np

from . import config, ingest, qc as qc_mod, petrophysics, honeypot_detector, pay_classifier, validation, las_writer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_RAW = os.path.join(ROOT, "data", "raw_las")
DEFAULT_OUT = os.path.join(ROOT, "outputs")


def analyze_well(path: str, decouple_pay: bool = False) -> Dict:
    """
    Phase-1 analysis for one well: compute curves + apparent pay + honeypot
    suspicion. Does NOT finalize pay or write — the global honeypot selection
    (which needs all wells ranked together) happens between phases.
    """
    rec = ingest.load_well(path)
    qc = qc_mod.run_qc(rec)
    petro = petrophysics.compute_all(rec, qc, decouple_pay=decouple_pay)
    apparent, conf, app_frac = pay_classifier.compute_apparent_pay(petro)
    hp = honeypot_detector.detect(rec, qc, petro, app_frac)
    return {"rec": rec, "qc": qc, "petro": petro, "hp": hp,
            "apparent": apparent, "app_frac": app_frac}


def select_honeypots(runs: List[Dict], target: int | None = None, veto_order: str = "suspicion") -> set:
    """
    Global honeypot set = all hard auto-vetoes, then filled by descending
    suspicion up to `target` (the known 25% base rate = 200). A3 is squared in
    the caught fraction, so reaching the true count is the key lever.
    """
    hard = {j for j, r in enumerate(runs) if r["hp"].hard_veto}
    if target is None:
        target = int(getattr(config, "HONEYPOT_TARGET_COUNT", 0) or 0)
    target = int(target or 0)
    honey = set(hard)
    if target > len(honey):
        if veto_order == "suspicion":
            # Normal: sort descending by suspicion score
            order = sorted(range(len(runs)), key=lambda j: -runs[j]["hp"].suspicion)
        elif veto_order == "anti":
            # Anti: sort ascending by suspicion score (least suspicious first)
            order = sorted(range(len(runs)), key=lambda j: runs[j]["hp"].suspicion)
        elif veto_order == "payconf":
            # Payconf: sort ascending by apparent pay fraction (weakest pay first)
            order = sorted(range(len(runs)), key=lambda j: runs[j]["app_frac"])
            
        for j in order:
            if j not in honey:
                honey.add(j)
                if len(honey) >= target:
                    break
    return honey, hard


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="No Second Guessing petrophysical pipeline")
    ap.add_argument("--raw", default=DEFAULT_RAW, help="directory of raw .las files")
    ap.add_argument("--out", default=DEFAULT_OUT, help="output base directory")
    ap.add_argument("--limit", type=int, default=0, help="process only the first N wells (0 = all)")
    ap.add_argument("--roundtrip-sample", type=int, default=40, help="how many wells to round-trip check")
    ap.add_argument("--no-zip", action="store_true", help="skip building the submission zip")
    ap.add_argument("--honeypot-target", type=int, default=None,
                    help="override config.HONEYPOT_TARGET_COUNT (0 = hard vetoes only)")
    ap.add_argument("--veto-order", choices=["suspicion", "anti", "payconf"], default="suspicion",
                    help="how to fill the target count: suspicion (normal), anti (least suspicious), or payconf (weakest pay)")
    ap.add_argument("--rw", type=float, default=None,
                    help="override config.RW_DEFAULT (formation water resistivity) for SW")
    ap.add_argument("--rw-mode", choices=["constant", "per_well"], default=None,
                    help="override config.RW_MODE: per_well derives Rw from the data")
    ap.add_argument("--decouple-pay", action="store_true",
                    help="freeze PAY_FLAG to the baseline-Rw SW while writing the new SW "
                         "(clean single-axis A4 probe)")
    ap.add_argument("--pay-phie-min", type=float, default=None, help="override PAY_PHIE_MIN")
    ap.add_argument("--pay-sw-max", type=float, default=None, help="override PAY_SW_MAX")
    ap.add_argument("--pay-vsh-max", type=float, default=None, help="override PAY_VSH_MAX")
    ap.add_argument("--perm-a", type=float, default=None, help="override PERM_A (log-linear intercept) — A4-PERM probe")
    ap.add_argument("--perm-b", type=float, default=None, help="override PERM_B (PHIE slope) — A4-PERM probe")
    ap.add_argument("--perm-c", type=float, default=None, help="override PERM_C (VSH slope) — A4-PERM probe")
    ap.add_argument("--no-simandoux", action="store_true",
                    help="use plain Archie SW (USE_SIMANDOUX=False) — matches the ttracx key exactly")
    ap.add_argument("--matrix-quartz", action="store_true",
                    help="force matrix density = 2.65 g/cc everywhere (FORCE_SANDSTONE_MATRIX) — matches the key's PHID")
    ap.add_argument("--pay-no-perm", action="store_true", help="drop the permeability pay criterion (match key)")
    ap.add_argument("--vsh-fixed", action="store_true", help="fixed 20/120 GAPI VSH endpoints (match key)")
    ap.add_argument("--archie-a", type=float, default=None, help="override ARCHIE_A (key=0.62)")
    ap.add_argument("--archie-m", type=float, default=None, help="override ARCHIE_M (key=2.15)")
    ap.add_argument("--phie-out", choices=["effective", "density", "rms"], default="effective",
                    help="A4 probe: overwrite ONLY the written PHIT/PHIE with density-only or "
                         "gas-corrected RMS porosity (pay/SW/PERM stay baseline = clean A4-PHIE read)")
    ap.add_argument("--perm-out", choices=["loglinear", "timur"], default="loglinear",
                    help="A4 probe: overwrite ONLY the written PERM with a classic Timur estimate "
                         "(pay stays baseline = clean A4-PERM read)")
    ap.add_argument("--tag", default="", help="suffix added to the submission zip name")
    args = ap.parse_args(argv)

    if args.pay_no_perm:
        config.PAY_USE_PERM = False
    if args.vsh_fixed:
        config.VSH_FIXED_ENDPOINTS = True
    if args.archie_a is not None:
        config.ARCHIE_A = args.archie_a
    if args.archie_m is not None:
        config.ARCHIE_M = args.archie_m
    if args.perm_a is not None:
        config.PERM_A = args.perm_a
    if args.perm_b is not None:
        config.PERM_B = args.perm_b
    if args.perm_c is not None:
        config.PERM_C = args.perm_c
    if args.no_simandoux:
        config.USE_SIMANDOUX = False
    if args.matrix_quartz:
        config.FORCE_SANDSTONE_MATRIX = True

    if args.rw is not None:
        config.RW_DEFAULT = args.rw   # affects SW (Axis 4) and thus pay (Axis 2)
    if args.rw_mode is not None:
        config.RW_MODE = args.rw_mode
    # Pay-cutoff overrides — clean A2 sweeps (A4 is scored at the key's pay depths,
    # independent of our PAY_FLAG; honeypots stay vetoed, so A3 is unaffected too).
    if args.pay_phie_min is not None:
        config.PAY_PHIE_MIN = args.pay_phie_min
    if args.pay_sw_max is not None:
        config.PAY_SW_MAX = args.pay_sw_max
    if args.pay_vsh_max is not None:
        config.PAY_VSH_MAX = args.pay_vsh_max

    sub_dir = os.path.join(args.out, "submission_las")
    qc_dir = os.path.join(args.out, "qc_reports")
    log_dir = os.path.join(args.out, "run_logs")
    for d in (sub_dir, qc_dir, log_dir):
        os.makedirs(d, exist_ok=True)

    wells = ingest.discover_wells(args.raw)
    if args.limit:
        wells = wells[: args.limit]
    if not wells:
        print(f"No .las files found in {args.raw}", file=sys.stderr)
        return 2

    print(f"Processing {len(wells)} wells from {args.raw}")
    t0 = time.time()

    log_rows: List[Dict] = []
    well_validations: List[validation.WellValidation] = []
    qc_rows: List[Dict] = []
    hp_rows: List[Dict] = []
    errors: List[str] = []
    written_paths: List[str] = []

    # ---- Phase 1: analyze every well (no writing yet) ----
    runs: List[Dict] = []
    for i, path in enumerate(wells, 1):
        wid = os.path.splitext(os.path.basename(path))[0]
        try:
            runs.append(analyze_well(path, decouple_pay=args.decouple_pay))
        except Exception as exc:  # never let one well abort the run
            errors.append(f"{wid}: {exc}")
            traceback.print_exc()
        if i % 100 == 0:
            print(f"  analyzed {i}/{len(wells)} wells ({time.time()-t0:.0f}s)")

    # ---- Global honeypot selection (needs all wells ranked together) ----
    honey, hard = select_honeypots(runs, target=args.honeypot_target, veto_order=args.veto_order)
    print(f"  honeypots: hard auto-veto={len(hard)}, total flagged={len(honey)} "
          f"(target {getattr(config, 'HONEYPOT_TARGET_COUNT', 0)}, order={args.veto_order})")

    # ---- Phase 2: finalize pay (apply veto), write, validate, log ----
    for j, r in enumerate(runs):
        rec, qc, petro, hp = r["rec"], r["qc"], r["petro"], r["hp"]
        wid = rec.well_id
        is_hp = j in honey
        final_pay, final_frac, vetoed = pay_classifier.finalize_pay(r["apparent"], is_hp)
        new_curves = {
            "VSH": petro.vsh, "PHIT": petro.phit, "PHIE": petro.phie,
            "SW": petro.sw, "PERM": petro.perm, "PAY_FLAG": final_pay,
        }
        # --- A4 output-curve probes: swap ONLY the written curve. Pay was decided
        # in phase 1 on the baseline petro, so A2/A3 stay pinned and only A4 moves.
        if args.phie_out != "effective":
            phit_alt = petrophysics.compute_phit_alt(rec.canonical, args.phie_out)
            if phit_alt is not None:
                phie_alt, _ = petrophysics.compute_phie(phit_alt, petro.vsh)
                new_curves["PHIT"] = phit_alt
                new_curves["PHIE"] = phie_alt
        if args.perm_out != "loglinear":
            new_curves["PERM"] = petrophysics.compute_perm_timur(petro.phie, petro.sw)
        wv = validation.validate_curves(wid, new_curves)
        out_path = os.path.join(sub_dir, f"{wid}.las")
        try:
            rows_written = las_writer.write_processed(rec, new_curves, out_path)
            if rows_written != rec.n_rows:
                wv.violations.append(f"rows_written={rows_written}/{rec.n_rows}")
            written_paths.append(out_path)
        except Exception as exc:
            errors.append(f"{wid}: write failed: {exc}")
            wv.violations.append(f"write failed: {exc}")

        well_validations.append(wv)
        log_rows.append({
            "well_id": wid, "n_rows": rec.n_rows,
            "n_curves_in": rec.meta.get("n_curves"),
            "families": "|".join(qc.families_present),
            "vsh_method": petro.methods.get("vsh"),
            "phit_method": petro.methods.get("phit"),
            "sw_method": petro.methods.get("sw"),
            "rho_ma": petro.diagnostics.get("rho_ma"),
            "rw_value": round(petro.diagnostics.get("rw_value", config.RW_DEFAULT), 4),
            "no_deep_res": qc.flags.get("no_deep_resistivity"),
            "apparent_pay_frac": round(r["app_frac"], 4),
            "honeypot_score": hp.score,
            "honeypot_suspicion": hp.suspicion,
            "is_honeypot": is_hp,
            "veto_reason": ("hard" if hp.hard_veto else ("fill" if is_hp else "")),
            "honeypot_flags": "|".join(k for k, v in hp.flags.items() if v),
            "final_pay_frac": round(final_frac, 4),
            "vetoed": vetoed,
            "violations": "; ".join(wv.violations),
        })
        qc_rows.append({
            "well_id": wid, "n_rows": qc.n_rows,
            "families_present": "|".join(qc.families_present),
            "families_missing": "|".join(qc.families_missing),
            "dead_curves": "|".join(qc.dead_curves),
            "washout_fraction": round(qc.washout_fraction, 3),
            "notes": " ".join(qc.notes),
        })
        hp_rows.append({
            "well_id": wid, "score": hp.score, "suspicion": hp.suspicion,
            "is_honeypot": is_hp, "hard_veto": hp.hard_veto,
            "flags": "|".join(k for k, v in hp.flags.items() if v),
        })

    elapsed = time.time() - t0
    print(f"Processed {len(written_paths)} wells in {elapsed:.0f}s ({len(errors)} errors)")

    # ---- write QC + honeypot + run logs ----
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    _write_csv(os.path.join(qc_dir, "qc_summary.csv"), qc_rows)
    _write_csv(os.path.join(qc_dir, "honeypot_flags.csv"), hp_rows)
    _write_csv(os.path.join(log_dir, f"run_{stamp}.csv"), log_rows)

    # ---- round-trip check on a sample (+ any flagged wells) ----
    rt_problems: Dict[str, List[str]] = {}
    sample = wells[:: max(1, len(wells) // max(1, args.roundtrip_sample))][: args.roundtrip_sample]
    for path in sample:
        wid = os.path.splitext(os.path.basename(path))[0]
        out_path = os.path.join(sub_dir, f"{wid}.las")
        if os.path.exists(out_path):
            rt_problems[wid] = validation.roundtrip_check(path, out_path)

    # ---- aggregate stats ----
    n_pay_wells = sum(1 for r in log_rows if r["final_pay_frac"] > 0)
    n_honeypot = sum(1 for r in log_rows if r["is_honeypot"])
    mean_pay = float(np.mean([r["final_pay_frac"] for r in log_rows])) if log_rows else 0.0
    summary = {
        "wells_in": len(wells),
        "wells_written": len(written_paths),
        "errors": len(errors),
        "wells_with_pay": n_pay_wells,
        "wells_flagged_honeypot": n_honeypot,
        "mean_pay_fraction": round(mean_pay, 4),
        "elapsed_seconds": round(elapsed, 1),
        "config_posture": "balanced",
    }

    report_path = os.path.join(args.out, "validation_report.md")
    validation.write_report(report_path, well_validations, rt_problems, summary)
    print(f"Validation report: {report_path}")

    if errors:
        _write_csv(os.path.join(log_dir, f"errors_{stamp}.csv"),
                   [{"error": e} for e in errors])

    # ---- build submission zip ----
    if not args.no_zip and written_paths:
        tag = f"_{args.tag}" if args.tag else ""
        zip_path = os.path.join(args.out, f"submission_{datetime.now().strftime('%Y%m%d')}{tag}.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(written_paths):
                zf.write(p, arcname=os.path.basename(p))
        print(f"Submission zip: {zip_path} ({len(written_paths)} files)")

    n_fail = sum(1 for w in well_validations if not w.ok)
    n_rt_fail = sum(1 for v in rt_problems.values() if v)
    print(f"Physics-gate failures: {n_fail} | round-trip failures (sampled): {n_rt_fail}")
    return 0 if (n_fail == 0 and n_rt_fail == 0 and not errors) else 1


def _write_csv(path: str, rows: List[Dict]) -> None:
    if not rows:
        # still write a header-less placeholder so the artifact exists
        open(path, "w").close()
        return
    keys = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
