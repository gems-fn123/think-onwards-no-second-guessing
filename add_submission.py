import json

with open("outputs/dashboard/submissions.json", "r") as f:
    data = json.load(f)

data["submissions"].append({
    "id": "PREC_400_sw035",
    "label": "Precision features at hp=400, sw=0.35",
    "date": "2026-06-28",
    "status": "queued",
    "score": None,
    "anchor": "H3",
    "isolates": "A3",
    "footage": 0.062,
    "change": "Day-2 precision features + honeypot_target=400 + PAY_SW_MAX=0.35"
})

with open("outputs/dashboard/submissions.json", "w") as f:
    json.dump(data, f, indent=2)
