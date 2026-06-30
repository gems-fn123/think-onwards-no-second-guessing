"""
Honeypot metadata/structure classifier probe (the final, CV-refuted gamble).

Question: can the ~200 honeypots be separated from the ~600 real wells using
LAS metadata + file-structure features, learned semi-supervised from the 135
hard-veto (physics-impossible = confirmed synthetic) wells as positive labels?

Result (2026-06-30): 5-fold CV AUC = 0.55 ≈ random. The metadata is
deliberately non-leaky. kimi's "date_style AUC 0.74" was overfit/in-sample —
honest enrichment is non-standard-date 18.5% hard-veto vs 16.9% baseline
(noise); high-veto company 30% (1.8x, 70% false positives). This closed the
last door before spending a leaderboard slot. See AGENT_BRIEF.md §17.

Run from repo root:  python scripts/honeypot_clf_probe.py
Needs: data/raw_las/*.las and a current outputs/qc_reports/honeypot_flags.csv
(regenerate the latter with `python -m src.main --no-zip` if missing).
"""
import os, re, glob, csv
import numpy as np
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw_las")
FLAGS = os.path.join(ROOT, "outputs", "qc_reports", "honeypot_flags.csv")

lab = {r["well_id"]: (1 if str(r.get("hard_veto", "")).lower() in ("true", "1") else 0)
       for r in csv.DictReader(open(FLAGS))}

DATE_STD = [r"^\d{1,2}/\d{1,2}/\d{2,4}$", r"^\d{4}-\d{2}-\d{2}$",
            r"^\d{1,2}-[A-Z]{3}-\d{4}$", r"^\d{8}$"]

def hdr_field(text, key):
    m = re.search(rf"(?mi)^\s*{key}\s*\.", text)
    if not m:
        return None
    line = text[m.start():text.find("\n", m.start())]
    parts = line.split(":", 1)[0]
    val = parts.split(".", 1)[1] if "." in parts else parts
    return val.strip()

def feats(path):
    raw = open(path, encoding="utf-8", errors="ignore").read()
    f = {"bytes": len(raw), "n_lines": len(raw.splitlines())}
    date = hdr_field(raw, "DATE")
    if date:
        du = date.upper().strip()
        f["date_nonstd"] = 0 if any(re.match(p, du) for p in DATE_STD) else 1
        f["date_len"] = len(du)
        f["date_has_alpha"] = 1 if re.search(r"[A-Z]{3,}", du) else 0
    else:
        f["date_nonstd"] = f["date_len"] = f["date_has_alpha"] = 0
    for k in ("STRT", "STOP", "STEP", "NULL"):
        v = hdr_field(raw, k)
        try:
            f[k.lower()] = float(re.findall(r"-?\d+\.?\d*", v)[0]) if v else 0.0
        except Exception:
            f[k.lower()] = 0.0
    nv = hdr_field(raw, "NULL") or ""
    f["null_dec"] = len(nv.split(".")[1]) if "." in nv else 0
    di = raw.upper().find("~A")
    decs, fw = [], []
    if di >= 0:
        for ln in raw[di:].splitlines()[1:200]:
            toks = ln.split()
            for t in toks:
                if "." in t:
                    decs.append(len(t.split(".")[1].split("E")[0]))
            if toks:
                fw.append(len(ln))
    f["data_dec"] = Counter(decs).most_common(1)[0][0] if decs else 0
    f["line_w"] = Counter(fw).most_common(1)[0][0] if fw else 0
    ci = raw.upper().find("~C")
    cnames = []
    if ci >= 0:
        for ln in raw[ci:di if di > ci else len(raw)].splitlines()[1:]:
            ln = ln.strip()
            if ln and not ln.startswith("#") and "." in ln:
                cnames.append(ln.split(".")[0].strip().upper())
    f["n_curves"] = len(cnames)
    for mn in ("GR", "RHOB", "NPHI", "DT", "RT", "PEF", "CALI", "SP", "DRHO", "RXO"):
        f[f"has_{mn}"] = 1 if mn in cnames else 0
    return f, (hdr_field(raw, "COMP") or "").strip()

rows, comps, y = [], [], []
for p in sorted(glob.glob(os.path.join(RAW, "*.las"))):
    w = os.path.splitext(os.path.basename(p))[0]
    if w not in lab:
        continue
    fe, comp = feats(p)
    rows.append(fe); comps.append(comp); y.append(lab[w])
y = np.array(y)
keys = sorted(rows[0].keys())
X = np.array([[r.get(k, 0.0) for k in keys] for r in rows], dtype=float)
top = [c for c, _ in Counter(comps).most_common(15)]
comp_oh = np.array([[1.0 if c == t else 0.0 for t in top] for c in comps])
Xf = np.hstack([X, comp_oh])
print(f"wells={len(y)} positives(hard_veto)={int(y.sum())} features={Xf.shape[1]}")

from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import cross_val_predict, StratifiedKFold
from sklearn.metrics import roc_auc_score

cv = StratifiedKFold(5, shuffle=True, random_state=0)
for name, clf in [("logreg", make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))),
                  ("gbm", GradientBoostingClassifier(random_state=0))]:
    proba = cross_val_predict(clf, Xf, y, cv=cv, method="predict_proba")[:, 1]
    print(f"  {name} 5-fold CV AUC = {roc_auc_score(y, proba):.3f}")
