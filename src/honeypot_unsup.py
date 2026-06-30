"""
Unsupervised honeypot anomaly scorer (the proper unsupervised method).

Builds a rich multivariate curve-feature matrix over all wells, fits an
IsolationForest + a 2-component GMM (NO labels), and writes a per-well
ensemble anomaly score to outputs/unsup_scores.csv. Higher = more
honeypot-like (more anomalous vs the population).

main.py --unsup-rank outputs/unsup_scores.csv then fills the honeypot soft
band by this score instead of the physics suspicion rank — isolating the
question: can an unsupervised model surface the physics-CLEAN honeypots that
the suspicion rank (≈ random past the 135 hard vetoes) cannot?

    python -m src.honeypot_unsup            # writes outputs/unsup_scores.csv
"""
from __future__ import annotations

import csv
import glob
import os
import warnings

import numpy as np

from . import ingest

warnings.simplefilter("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRIM = ["GR", "RHOB", "NPHI", "DT", "RT", "PEF", "CAL", "SP"]
PAIRS = [("GR", "RHOB"), ("RHOB", "NPHI"), ("GR", "RT"), ("RHOB", "DT")]


def _well_features(rec) -> list:
    """52-dim curve signature: per-curve moments/autocorr/uniqueness + cross-corrs."""
    can = rec.canonical
    f = []
    for fam in PRIM:
        v = can.get(fam, {}).get("values") if fam in can else None
        if v is None:
            f += [0.0] * 6
            continue
        x = np.asarray(v, dtype=float)
        x = x[np.isfinite(x)]
        if x.size < 30:
            f += [0.0] * 6
            continue
        ac = float(np.corrcoef(x[:-1], x[1:])[0, 1]) if np.std(x) > 1e-9 else 0.0
        f += [float(np.mean(x)), float(np.std(x)), float(np.percentile(x, 10)),
              float(np.percentile(x, 90)), ac, x.size and np.unique(x).size / x.size]
    for a, b in PAIRS:
        va = can.get(a, {}).get("values") if a in can else None
        vb = can.get(b, {}).get("values") if b in can else None
        if va is None or vb is None:
            f.append(0.0)
            continue
        va = np.asarray(va, dtype=float); vb = np.asarray(vb, dtype=float)
        m = np.isfinite(va) & np.isfinite(vb)
        f.append(float(np.corrcoef(va[m], vb[m])[0, 1])
                 if m.sum() > 30 and np.std(va[m]) > 1e-9 and np.std(vb[m]) > 1e-9 else 0.0)
    return f


def compute_unsup_scores(raw_dir: str) -> dict:
    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import IsolationForest
    from sklearn.mixture import GaussianMixture

    wells = sorted(glob.glob(os.path.join(raw_dir, "*.las")))
    wid, X = [], []
    for p in wells:
        try:
            rec = ingest.load_well(p)
        except Exception:
            continue
        wid.append(rec.well_id)
        X.append(_well_features(rec))
    X = np.nan_to_num(np.array(X, dtype=float))
    Xs = StandardScaler().fit_transform(X)

    iso = IsolationForest(contamination=0.25, random_state=0).fit(Xs)
    iso_an = -iso.score_samples(Xs)               # higher = more anomalous

    gm = GaussianMixture(2, random_state=0).fit(Xs)
    post = gm.predict_proba(Xs)
    minority = int(np.argmin(np.bincount(gm.predict(Xs))))  # smaller cluster = anomalous
    gmm_an = post[:, minority]

    def _z(a):
        s = np.std(a)
        return (a - np.mean(a)) / s if s > 1e-9 else a * 0.0

    score = _z(iso_an) + _z(gmm_an)               # unsupervised ensemble
    return {w: float(s) for w, s in zip(wid, score)}


def main(argv=None) -> int:
    raw_dir = os.path.join(ROOT, "data", "raw_las")
    out = os.path.join(ROOT, "outputs", "unsup_scores.csv")
    scores = compute_unsup_scores(raw_dir)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["well_id", "unsup_score"])
        for k, v in sorted(scores.items(), key=lambda t: -t[1]):
            w.writerow([k, f"{v:.6f}"])
    print(f"wrote {len(scores)} unsup scores -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
