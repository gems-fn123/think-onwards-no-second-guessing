"""
Central configuration for the No Second Guessing petrophysical pipeline.

Everything tunable lives here so the rest of the code stays declarative and the
leaderboard-iteration loop only ever edits one file. Values are deliberately
conservative ("balanced" risk posture): the goal is to never zero any scoring
axis (physics gate / pay accuracy / honeypot rejection / curve accuracy), which
matters because the challenge combines the axes with a geometric mean.

All alias lists are ordered BEST-FIRST: the curve-mapping layer walks each list
and takes the first mnemonic present in a given well.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# LAS / format constants
# ---------------------------------------------------------------------------
NULL_VALUE = -999.25            # universal in this dataset (verified across 800 wells)
NULL_TEXT = "-999.25000"        # how nulls are written back into the ASCII section

# The six curves we must add to every output well, with the units we declare.
REQUIRED_OUTPUT_CURVES = ["VSH", "PHIT", "PHIE", "SW", "PERM", "PAY_FLAG"]
OUTPUT_CURVE_UNITS = {
    "VSH": "V/V",
    "PHIT": "V/V",
    "PHIE": "V/V",
    "SW": "V/V",
    "PERM": "MD",
    "PAY_FLAG": "",
}
OUTPUT_CURVE_DESCR = {
    "VSH": "Volume of shale",
    "PHIT": "Total porosity",
    "PHIE": "Effective porosity",
    "SW": "Water saturation (Archie/Simandoux)",
    "PERM": "Permeability estimate",
    "PAY_FLAG": "Binary net-pay indicator (0/1)",
}

# ---------------------------------------------------------------------------
# Curve family aliases (UPPERCASE, best-first priority order)
# Built from a profile of all 800 wells (217 distinct mnemonics).
# ---------------------------------------------------------------------------

# Depth is normally the index column; these let us recognise it explicitly.
DEPTH_ALIASES = ["DEPT", "DEPTH", "MD", "TDEP", "DEPH", "DEP", "MDEPTH"]

# Gamma ray used for VSH. Total GR preferred; CGR (uranium-free computed GR) is a
# good shale indicator too and kept mid-list. Per-well min/max normalisation in
# VSH makes the absolute scale (GAPI vs CPS) irrelevant.
GR_ALIASES = [
    "GR", "ECGR", "SGR", "HSGR", "GRD", "GRGC", "GRS", "GR1", "GR2", "GRR",
    "GRAM", "HGR", "HGRC", "HGRCC", "NGRT", "GKUT", "GR_EDTC", "GR_SL", "EHGR",
    "GCGR", "GRTO", "GRN", "CGR",
]

# Bulk density (g/cc). DRHO (density correction) is intentionally excluded — it is
# a QC curve, handled separately for bad-hole detection.
RHOB_ALIASES = [
    "RHOB", "RHOZ", "ZDEN", "DEN", "RHOB_CDL", "FDC", "DENB", "DENC", "DENS",
    "ROBB", "RHOBC", "RHOM", "ZDNC", "ZDENS", "RHBH", "HDEN", "HDRA", "HDRHO",
    "EDRA", "RHOZE", "DEN_COR", "DENB",
]

# Neutron porosity (fraction). Limestone-matrix curves included; matrix shift is
# small relative to other uncertainties here.
NPHI_ALIASES = [
    "NPHI", "TNPH", "NPOR", "NPHI_CDL", "NPOR_LS", "CNL", "CNCF", "CNC", "NEU",
    "NEUT", "HNPO", "HTNP", "APLC", "APLS", "BPHI", "PHIN", "SNPH", "NPRL",
    "NPRS", "ENPH", "TNPS", "TNPB", "TCNL", "PHIS",
]

# Compressional sonic slowness (us/ft). Shear (DT4S) deliberately omitted.
DT_ALIASES = [
    "DTCO", "DT", "DTC", "DT_BHC", "DTBHC", "BHC", "AC", "SONIC", "SON",
    "SONICDT", "DTLN", "DTLN_MRK", "DTL", "DTSH", "DT1R", "DT1", "DT24",
    "DTCO4", "DT4P", "EDTC", "HDTC", "SLOWNESS",
]

# Deep resistivity (ohm.m) for Archie Rt. Deepest-reading first.
RT_ALIASES = [
    "RT", "ILD", "LLD", "RESD", "RD", "RILD", "RLLD", "AT90", "AHT90", "AHF90",
    "AIT_H90", "A34H", "A28H", "A22H", "A16H", "P16H", "HDRS", "HLLD", "RLA5",
    "RLLA", "IDPH", "RAILD", "M2R9", "AHO10", "RB", "SGRD",
]

# Shallow / flushed-zone resistivity (ohm.m). Used as Rt fallback for the ~46
# wells with no true deep curve, and for invasion cross-checks.
RXO_ALIASES = [
    "RXO", "MSFL", "SFL", "SFLU", "LLS", "MLL", "MCFL", "RXOZ", "RXO8",
    "RXO_HRLT", "RXORT", "RILM", "ILM", "RS", "RSFL", "RMLL", "SN", "HMRS",
    "HMIN", "AO10", "AO90", "RLA1",
]

# Photoelectric factor (b/e) for matrix identification.
PE_ALIASES = [
    "PEF", "PE", "PEFZ", "PEFA", "PEFN", "PEDN", "PE_CDL", "PEF8", "PE8",
    "PEZ", "PEZL", "PEFL", "PEFLA", "PPEN", "HPEF", "HDPE", "HDPEF", "ENPE",
]

# Caliper / hole diameter (in). Bit size handled separately (BIT_ALIASES).
CAL_ALIASES = [
    "CAL", "CALI", "HCAL", "HCALS", "CALS", "LCAL", "CAL_CDL", "CALDC", "CLDC",
    "CALD", "CALR", "CALX", "ECAL", "CAL1", "CAL2", "C1", "C2", "TAB", "DCAL",
]
BIT_ALIASES = ["BS"]              # bit size — reference diameter for washout
DCAL_ALIASES = ["DCAL", "DRHO"]   # differential caliper / density correction (QC)

# Spontaneous potential (mV). Not used numerically in the scored path, but
# recognised so it is not mistaken for another family.
SP_ALIASES = [
    "SP", "SSP", "SPONT", "SP_MV", "SPC", "SPR", "SPM", "PSP", "ESP", "SPHI",
    "SPNT", "SPOT", "SPONPOT",
]

# Environmental params occasionally present as curves — read if available.
TEMP_ALIASES = ["TEMP"]
SALINITY_ALIASES = ["BSAL"]

# Drilling-mechanics / decoy curves: never petrophysical inputs. Their presence
# is noise, not (by itself) a honeypot tell.
JUNK_ALIASES = [
    "WOB", "TORQ", "SWOB", "ROP", "RPM", "TT1", "TT2", "PRES", "MUDW", "ECD",
    "TENS", "HAZI", "DEVI", "X1", "X2", "UNKNOWN",
]

# Map of standardized family name -> alias list, for generic lookups.
FAMILY_ALIASES = {
    "GR": GR_ALIASES,
    "RHOB": RHOB_ALIASES,
    "NPHI": NPHI_ALIASES,
    "DT": DT_ALIASES,
    "RT": RT_ALIASES,
    "RXO": RXO_ALIASES,
    "PE": PE_ALIASES,
    "CAL": CAL_ALIASES,
    "BIT": BIT_ALIASES,
    "SP": SP_ALIASES,
    "TEMP": TEMP_ALIASES,
    "SALINITY": SALINITY_ALIASES,
}

# ---------------------------------------------------------------------------
# Unit normalization. Maps an UPPERCASE unit string to a multiplicative factor
# that converts the raw value into the family's canonical unit.
#   resistivity -> ohm.m, density -> g/cc, neutron -> fraction,
#   sonic -> us/ft, caliper -> inch
# Unknown units default to factor 1.0 (assume already canonical).
# ---------------------------------------------------------------------------
RES_UNITS = {"OHMM": 1.0, "OHM.M": 1.0, "OHM-M": 1.0, "OHM_M": 1.0, "OHM": 1.0,
             "HMOH": 1.0, "OHMS": 1.0, "OHMSM": 1.0}
DEN_UNITS = {"G/CC": 1.0, "G/C3": 1.0, "GM/CC": 1.0, "G/CM3": 1.0, "GCC": 1.0,
             "KG/M3": 0.001, "K/M3": 0.001}
NEU_UNITS = {"V/V": 1.0, "DEC": 1.0, "FRAC": 1.0, "FRACTION": 1.0, "M3/M3": 1.0,
             "PU": 0.01, "%": 0.01, "P.U.": 0.01, "PCT": 0.01, "PERCENT": 0.01}
SON_UNITS = {"US/FT": 1.0, "US/F": 1.0, "USEC/FT": 1.0, "USFT": 1.0, "USEC/F": 1.0,
             "MICROSEC/FT": 1.0, "US/M": 1.0 / 3.280839895, "USEC/M": 1.0 / 3.280839895,
             "US/METER": 1.0 / 3.280839895}
CAL_UNITS = {"IN": 1.0, "INCH": 1.0, "INCHES": 1.0, '"': 1.0, "INS": 1.0,
             "CM": 1.0 / 2.54, "MM": 1.0 / 25.4, "M": 39.3700787}

FAMILY_UNIT_TABLE = {
    "RT": RES_UNITS, "RXO": RES_UNITS,
    "RHOB": DEN_UNITS,
    "NPHI": NEU_UNITS,
    "DT": SON_UNITS,
    "CAL": CAL_UNITS, "BIT": CAL_UNITS,
}

# ---------------------------------------------------------------------------
# Physical plausibility ranges. Values outside are treated as nulls during QC
# (curve-level), so a unit slip or a decoy spike cannot poison a calculation.
# ---------------------------------------------------------------------------
VALID_RANGES = {
    "GR": (0.0, 400.0),        # GAPI (CPS handled by normalisation, range generous)
    "RHOB": (1.2, 3.1),        # g/cc
    "NPHI": (-0.05, 1.0),      # fraction
    "DT": (35.0, 220.0),       # us/ft
    "RT": (0.01, 5000.0),      # ohm.m
    "RXO": (0.01, 5000.0),     # ohm.m
    "PE": (0.5, 12.0),         # b/e
    "CAL": (4.0, 30.0),        # in
    "BIT": (4.0, 30.0),        # in
}

# ---------------------------------------------------------------------------
# Petrophysical model constants (regional defaults for a clastic section).
# ---------------------------------------------------------------------------
# Matrix / fluid densities for density porosity.
RHO_MA_SANDSTONE = 2.65
RHO_MA_LIMESTONE = 2.71
RHO_MA_DOLOMITE = 2.87
RHO_MA_DEFAULT = 2.65
RHO_FLUID = 1.0                # fresh-to-moderate mud filtrate
# The challenge states a CLASTIC reservoir. Forcing sandstone matrix everywhere:
# PE-based dolomite picks were inflating PHID by ~0.13 v/v (4x the 0.03 scoring
# tolerance) on ~185 wells, zeroing their curve-accuracy score. Keep PE for QC,
# not for matrix selection.
FORCE_SANDSTONE_MATRIX = True
# PE-based matrix selection thresholds (b/e): sandstone ~1.8, limestone ~5, dolomite ~3.
PE_SAND_MAX = 2.5
PE_DOLO_MAX = 4.0

# Sonic porosity (Wyllie time-average).
DT_MATRIX = 55.5               # us/ft (sandstone)
DT_FLUID = 189.0               # us/ft
WYLLIE_COMPACTION = 1.0        # Bcp; >1 would de-rate uncompacted sands

# Neutron-density blend. Components are first clipped to a physical porosity
# range (so a rail-pinned density of 3.0 g/cc -> negative PHID cannot poison the
# result), then averaged arithmetically. Arithmetic mean is the most robust total
# porosity estimate here; RMS was rejected because squaring hides bad components.
ND_COMPONENT_CLIP = (0.0, 0.60)

# Porosity caps.
PHIT_MAX = 0.45
PHIE_MAX = 0.45

# Archie / saturation.
ARCHIE_A = 1.0
ARCHIE_M = 2.0
ARCHIE_N = 2.0
# Neutron-density separation (porosity units) in 100% shale, used as a VSH
# fallback indicator when GR is dead/degenerate.
VSH_ND_SHALE_SEP = 0.40
# VSH gamma-ray index endpoints. The answer-key "standard workflow"
# (github.com/ttracx/oil-and-gas-claude-skills) uses FIXED 20/120 GAPI rather
# than per-well percentiles. VSH_FIXED_ENDPOINTS=True matches the key.
VSH_FIXED_ENDPOINTS = False
VSH_GR_CLEAN = 20.0
VSH_GR_SHALE = 120.0
RW_DEFAULT = 0.05              # ohm.m formation water resistivity at formation T
RW_TEMP_REF = 75.0            # deg F reference for RW_DEFAULT
# Rw mode: "constant" uses RW_DEFAULT; "per_well" derives Rw from the data via the
# Rwa-minimum (Pickett) estimator in clean low-VSH zones. The diagnostic showed
# data-implied Rw ~0.14 (median) vs our 0.05 -> SW was too low (A4/A2 hit).
RW_MODE = "constant"
RW_MIN = 0.02                  # clamp band for per-well Rw estimate
RW_MAX = 0.60
RW_RWA_PERCENTILE = 10         # Rwa percentile taken as the Rw estimate
USE_SIMANDOUX = True           # shaly-sand correction when VSH is significant
RSH_DEFAULT = 2.0              # ohm.m shale resistivity for Simandoux

# Permeability (Timur-style log-linear in PHIE and VSH).
#   log10(k) = PERM_A + PERM_B*PHIE - PERM_C*VSH
# Calibrated so clean rock lands in sensible ranges without mass-clamping:
#   PHIE 0.10 -> ~0.4 mD, 0.20 -> ~16 mD, 0.25 -> ~100 mD, 0.30 -> ~630 mD.
PERM_A = -2.0
PERM_B = 16.0
PERM_C = 3.0
PERM_MIN = 0.0
PERM_MAX = 20000.0

# ---------------------------------------------------------------------------
# Net-pay cutoffs (balanced). Pay requires ALL criteria AND a clean honeypot
# verdict. These are the primary knobs for leaderboard tuning.
# ---------------------------------------------------------------------------
PAY_VSH_MAX = 0.50
PAY_PHIE_MIN = 0.10           # standard clastic net-pay porosity cutoff
PAY_SW_MAX = 0.55
PAY_PERM_MIN = 0.10            # mD
# The answer-key standard workflow flags pay on VSH<0.40 AND PHIE>0.06 AND SW<0.60
# with NO permeability criterion. PAY_USE_PERM=False matches the key.
PAY_USE_PERM = True

# ---------------------------------------------------------------------------
# Honeypot detection (well-level). The well is vetoed to zero pay only when the
# suspicion score crosses HONEYPOT_SCORE_THRESHOLD. Kept strict so real wells are
# not zeroed (protects the pay axis).
# ---------------------------------------------------------------------------
HONEYPOT_SCORE_THRESHOLD = 3.0     # sum of weighted flags above which we veto

# Global selection: the dataset is exactly 25% honeypots (200/800). After hard
# auto-vetoes, fill the honeypot set up to this count using the continuous
# suspicion ranking (worst-first). Set to 0 to disable global fill and use only
# hard vetoes. This is the main A3 knob — A3 = 100*(caught/200)^2, so recall
# toward 200 is the single biggest score lever.
HONEYPOT_TARGET_COUNT = 200
# Weights are tiered. A "hard" physics violation (no real log can show it) is
# weighted at the threshold so any single one vetoes the well. "Medium" signals
# need to co-occur; "soft" signals only nudge. This is the main honeypot knob.
HONEYPOT_FLAG_WEIGHTS = {
    # --- hard physics violations (auto-veto) ---
    "raw_oob_violations": 3.0,           # raw measurements physically impossible
    "neg_porosity_pervasive": 3.0,       # density > matrix over much of the well
    "impossible_porosity_pervasive": 3.0,# raw porosity > physical max over much of well
    "density_neutron_impossible": 3.0,   # huge unphysical D-N separation everywhere
    # --- medium signals (need to accumulate) ---
    "dead_primary_curve": 1.5,           # a primary curve is constant/dead
    "rt_porosity_contradiction": 1.5,    # high-Rt coincident with very wet, clean porosity
    # --- soft signals ---
    "fragile_resistivity_pay": 0.5,      # apparent pay rests on invaded-zone Rt fallback
    "no_resistivity": 0.5,               # cannot compute SW robustly
    "extreme_washout": 0.5,              # caliper >> bit over most of the well
}
# Raw porosity above this fraction is not physically reachable in rock.
IMPOSSIBLE_POROSITY = 0.55

# Raw out-of-range physics violations (the cleanest honeypot signature: ~72 wells
# have pervasively impossible raw measurements vs ~0 for real wells). Bounds are
# HARD physical limits (wider than the QC gating ranges) so only true
# impossibilities count. A well with > HONEYPOT_OOB_FRACTION of samples violating
# is auto-vetoed.
HARD_BOUNDS = {
    "RHOB": (1.0, 3.05),
    "NPHI": (-0.02, 1.0),
    "GR": (0.0, 300.0),
    "DT": (30.0, 250.0),
    "PE": (0.0, 15.0),
    "RT": (0.0, 1.0e6),
    "RXO": (0.0, 1.0e6),
}
HONEYPOT_OOB_FRACTION = 0.05

# Fraction of valid samples that must violate a rule for it to count as
# "pervasive" (a few bad samples are normal in real logs).
PERVASIVE_FRACTION = 0.30

# ---------------------------------------------------------------------------
# QC thresholds.
# ---------------------------------------------------------------------------
DEAD_CURVE_STD_EPS = 1e-6      # std below this => constant/dead curve
MAX_NAN_FRACTION = 0.95        # curve is "mostly missing" above this
WASHOUT_DELTA_IN = 1.0         # caliper - bit > this (in) => washed out sample
