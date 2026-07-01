import glob, os, csv, numpy as np
from src.ingest import load_well
from src.petrophysics import compute_vsh, compute_phit, compute_phie, compute_sw
import src.config as config

config.VSH_FIXED_ENDPOINTS = True
config.RW_MODE = "constant"
config.RW_DEFAULT = 0.05

FLAGS = "outputs/qc_reports/honeypot_flags.csv"
lab = {r["well_id"]: (1 if str(r.get("hard_veto", "")).lower() in ("true", "1") else 0)
       for r in csv.DictReader(open(FLAGS))}

for f in glob.glob("data/raw_las/*.las")[:100]:
    try:
        rec = load_well(f)
        vsh, _ = compute_vsh(rec.canonical)
        if vsh is None: continue
        phit, _, _, _, _ = compute_phit(rec.canonical)
        phie, _ = compute_phie(phit, vsh)
        sw, _, _ = compute_sw(rec.canonical, phie, vsh, rec.meta.get("temp_surface", 75.0), rec.meta.get("temp_bottom", 150.0))
        
        pay = (vsh < 0.40) & (phie > 0.06) & (sw < 0.60)
        if not np.any(pay): continue
        
        depth = rec.canonical["DEPTH"]["values"] if "DEPTH" in rec.canonical else rec.curves[list(rec.curves.keys())[0]]["values"]
        
        pay_depths = depth[pay]
        if len(pay_depths) > 0:
            thickness = np.max(pay_depths) - np.min(pay_depths)
            w = os.path.splitext(os.path.basename(f))[0]
            if lab.get(w, 0) == 1:
                print("Honeypot", w, "thickness", thickness)
    except Exception as e:
        print(e)
