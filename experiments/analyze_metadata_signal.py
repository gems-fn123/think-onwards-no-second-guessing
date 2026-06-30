"""
Analyze LAS metadata features for honeypot-separating signal.

Run:
    cd /home/gems-fn123/think-onwards-no-second-guessing-kimchi
    python experiments/analyze_metadata_signal.py

Outputs:
    outputs/metadata_v2_analysis.json
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import config
from src.honeypot_detector import detect
from src.ingest import discover_wells, load_well
from src.metadata_detector import extract_metadata_features
from src import pay_classifier
from src import petrophysics
from src import qc as qc_mod


def _get_hard_veto_labels() -> dict:
    """Run detector on all wells and return hard_veto boolean per well_id."""
    labels = {}
    wells = discover_wells("data/raw_las")
    print(f"Running detector on {len(wells)} wells...")
    for path in wells:
        rec = load_well(path)
        qc = qc_mod.run_qc(rec)
        petro = petrophysics.compute_all(rec, qc)
        apparent_pay, conf, apparent_frac = pay_classifier.compute_apparent_pay(petro)
        result = detect(rec, qc, petro, apparent_frac)
        labels[rec.well_id] = bool(result.hard_veto)
    return labels


def _cohens_d(x1, x2) -> float:
    s1, s2 = np.std(x1, ddof=1), np.std(x2, ddof=1)
    n1, n2 = len(x1), len(x2)
    pooled = np.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2))
    if pooled == 0:
        return 0.0
    return float((np.mean(x1) - np.mean(x2)) / pooled)


def main():
    labels = _get_hard_veto_labels()
    wells = discover_wells("data/raw_las")

    rows = []
    for path in wells:
        rec = load_well(path)
        feat = extract_metadata_features(rec)
        row = {"well_id": rec.well_id, "hard_veto": int(labels[rec.well_id])}
        row.update(feat.detail)
        # Add categorical raw values too
        row["date_style"] = feat.date_style
        row["comp"] = feat.comp
        row["srvc"] = feat.srvc
        row["null_is_standard"] = int(feat.null_is_standard)
        row["line_ending"] = feat.line_ending
        rows.append(row)

    df = pd.DataFrame(rows)
    df["hard_veto"] = df["hard_veto"].astype(int)
    veto = df[df.hard_veto == 1]
    real = df[df.hard_veto == 0]
    baseline_rate = df.hard_veto.mean()

    numeric_cols = [c for c in df.columns if c.startswith("meta_") and c not in ("well_id", "hard_veto")]

    numeric_results = []
    for col in numeric_cols:
        x = df[col].fillna(df[col].median()).values
        x_v = veto[col].dropna().values
        x_r = real[col].dropna().values
        if len(x_v) < 5 or len(x_r) < 5:
            continue
        if len(np.unique(x)) < 2 or len(np.unique(df.hard_veto.values)) < 2:
            continue
        try:
            auc = roc_auc_score(df.hard_veto.values, x)
        except Exception:
            continue
        d = _cohens_d(x_v, x_r)
        numeric_results.append({
            "feature": col,
            "auc": round(float(auc), 4),
            "cohens_d": round(d, 4),
            "veto_mean": round(float(np.mean(x_v)), 6),
            "real_mean": round(float(np.mean(x_r)), 6),
        })

    numeric_results = sorted(numeric_results, key=lambda r: abs(r["auc"] - 0.5), reverse=True)

    # Categorical analysis
    cat_results = []
    for col in ["date_style", "comp", "srvc", "line_ending"]:
        cats = df[col].fillna("MISSING").unique()
        cat_stats = []
        for cat in cats:
            sub = df[df[col] == cat]
            rate = sub.hard_veto.mean()
            lift = rate / baseline_rate if baseline_rate > 0 else 0
            cat_stats.append({
                "value": cat,
                "count": int(len(sub)),
                "veto_rate": round(float(rate), 4),
                "lift": round(float(lift), 4),
            })
        cat_stats = sorted(cat_stats, key=lambda r: r["veto_rate"], reverse=True)
        cat_results.append({"feature": col, "categories": cat_stats[:10]})

    # Combined model using top numeric features
    top_features = [r["feature"] for r in numeric_results[:10]]
    X = df[top_features].fillna(df[top_features].median()).values
    y = df.hard_veto.values
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    model = LogisticRegression(max_iter=1000, C=1.0)
    model.fit(Xs, y)
    preds = model.predict_proba(Xs)[:, 1]
    combined_auc = roc_auc_score(y, preds)

    # Recommended weights (linear model coefficients, scaled and capped)
    coefs = model.coef_[0]
    max_abs = max(abs(coefs).max(), 1e-9)
    rec_weights = {}
    for feat, coef in zip(top_features, coefs):
        rec_weights[feat] = round(float(np.clip(coef / max_abs * 1.0, -2.0, 2.0)), 4)

    output = {
        "n_wells": len(df),
        "baseline_veto_rate": round(float(baseline_rate), 4),
        "hard_vetoes": int(df.hard_veto.sum()),
        "combined_model_auc": round(float(combined_auc), 4),
        "top_numeric_features": numeric_results[:15],
        "categorical_features": cat_results,
        "recommended_weights": rec_weights,
    }

    os.makedirs("outputs", exist_ok=True)
    with open("outputs/metadata_v2_analysis.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"Wells: {len(df)} | Hard vetoes: {df.hard_veto.sum()}")
    print(f"Combined model AUC: {combined_auc:.4f}")
    print("\nTop numeric features:")
    for r in numeric_results[:10]:
        print(f"  {r['feature']:30s} AUC={r['auc']:.4f} d={r['cohens_d']:+.3f} "
              f"veto={r['veto_mean']:.4f} real={r['real_mean']:.4f}")
    print("\nRecommended weights:")
    for k, v in rec_weights.items():
        print(f"  {k}: {v}")
    print("\nSaved outputs/metadata_v2_analysis.json")


if __name__ == "__main__":
    main()
