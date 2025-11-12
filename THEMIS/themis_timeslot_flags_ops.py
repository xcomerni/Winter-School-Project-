# This cell generates operational flags for each 100x100 grid cell and time fascia, 
# considering various temperature limits for rover and helicopter operations.

# themis_timeslot_flags_ops.py
# Flags for each of the 4 THEMIS fascias, including:
# - Per-slot QUALITY (outlier)                           -> THEMIS_OK_<slot>, THEMIS_reason_<slot>
# - ROVER limits (strict/soft)                           -> ROVER_OK_strict_<slot>, ROVER_OK_soft_<slot>, ROVER_reason_<slot>
# - HELICOPTER limits (Ingenuity-like, survival/energy)  -> HELI_survival_ok_<slot>, HELI_energy_pref_<slot>, HELI_reason_<slot>
# - Combined STRICT/SOFT                                 -> SLOT_GOOD_strict_<slot>, SLOT_REASON_strict_<slot>, SLOT_GOOD_soft_<slot>, SLOT_REASON_soft_<slot>

import pandas as pd
import numpy as np

IN_CSV  = "themis_ML_data_100x100.csv"
OUT_CSV = "themis_timeslot_flags_ops.csv"

# Time fascias (as in your CSV)
TIMES = ["5_30AM","7_00AM","6_30PM","7_00PM"]
COLS  = [f"mean_temperature_{t}" for t in TIMES]

# --- PARAMETERS ---

# 1) Wide physical window for QUALITY outliers (Martian environment, °C)
PHYS_MIN_C, PHYS_MAX_C = -120.0, 20.0

# 2) Adaptive per-slot thresholds (more severe to generate realistic BADs)
QUAL_Q_LOW, QUAL_Q_HIGH = 0.10, 0.90

# 3) OPERATIONAL limits — ROVER (environment)
COMP_MIN_C, COMP_MAX_C = -40.0, 40.0   # preferable for components (internal)
HEATER_MIN_C           = -100.0        # acceptable with heater (conservative)

# 4) Limits — HELICOPTER (Ingenuity-like, environment)
HELI_SURVIVAL_MIN_C    = -100.0        # nighttime survival
HELI_ENERGY_PREF_MIN_C = -70.0         # preferable for consumption/heaters

# 5) NEW: minimum STRICT threshold per slot (energy-friendly by slot)
#    - morning: slightly colder allowed
#    - evening: expected slightly warmer, less severe threshold (-60)
STRICT_MIN_BY_SLOT = {
    "5_30AM": -70.0,
    "7_00AM": -70.0,
    "6_30PM": -60.0,
    "7_00PM": -60.0,
}

def to_celsius_if_needed(df):
    """Converts Kelvin→°C if values appear to be in Kelvin (max > 200)."""
    mx = df[COLS].max(skipna=True).max()
    if pd.notna(mx) and mx > 200:
        df[COLS] = df[COLS] - 273.15
    return df

def main():
    df = pd.read_csv(IN_CSV)

    # Sanity check
    missing = [c for c in ["x","y"] + COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in CSV: {missing}")

    df = to_celsius_if_needed(df)

    for t, c in zip(TIMES, COLS):
        has_col      = f"has_{c}"
        q_ok_col     = f"THEMIS_OK_{t}"
        q_reason_col = f"THEMIS_reason_{t}"

        rover_ok_strict = f"ROVER_OK_strict_{t}"
        rover_ok_soft   = f"ROVER_OK_soft_{t}"
        rover_reason    = f"ROVER_reason_{t}"

        heli_surv_ok    = f"HELI_survival_ok_{t}"
        heli_energy_ok  = f"HELI_energy_pref_{t}"
        heli_reason     = f"HELI_reason_{t}"

        slot_good_strict = f"SLOT_GOOD_strict_{t}"
        slot_reason_str  = f"SLOT_REASON_strict_{t}"
        slot_good_soft   = f"SLOT_GOOD_soft_{t}"
        slot_reason_soft = f"SLOT_REASON_soft_{t}"

        # 1) Data present?
        df[has_col] = df[c].notna()

        # 2) Per-slot QUALITY (quantiles on pixels with data) + physical clip
        vals = df.loc[df[has_col], c]
        if len(vals) >= 10:
            lo_q, hi_q = vals.quantile(QUAL_Q_LOW), vals.quantile(QUAL_Q_HIGH)
        else:
            lo_q, hi_q = PHYS_MIN_C, PHYS_MAX_C

        lo_qual = max(lo_q, PHYS_MIN_C)
        hi_qual = min(hi_q, PHYS_MAX_C)

        df[q_ok_col] = df[has_col] & df[c].between(lo_qual, hi_qual, inclusive="both")

        def qual_reason(v, has):
            if not has or pd.isna(v): return "fail: themis_missing"
            if v < lo_qual:           return "fail: themis_too_cold_outlier"
            if v > hi_qual:           return "fail: themis_too_warm_outlier"
            return "good"
        df[q_reason_col] = [qual_reason(v, h) for v, h in zip(df[c], df[has_col])]

        # 3) ROVER — strict/soft per slot
        strict_min = STRICT_MIN_BY_SLOT[t]

        def rover_flags(v, has):
            if not has or pd.isna(v): return False, False, "missing"
            if v > COMP_MAX_C:        return False, False, "too_hot"
            # strict: energy-friendly per slot (>= strict_min) and <= +40
            strict_ok = v >= strict_min
            # soft: acceptable with heater (>= -100) and <= +40
            soft_ok   = v >= HEATER_MIN_C
            # descriptive reason
            if v >= COMP_MIN_C:   rr = "ideal"
            elif v >= strict_min: rr = "energy_pref_slot"
            elif v >= HEATER_MIN_C: rr = "heater_needed"
            else:                 rr = "too_cold"
            return strict_ok, soft_ok, rr

        s_ok, sf_ok, r_r = [], [], []
        for v, h in zip(df[c], df[has_col]):
            so, sfo, rr = rover_flags(v, h)
            s_ok.append(so); sf_ok.append(sfo); r_r.append(rr)
        df[rover_ok_strict] = s_ok
        df[rover_ok_soft]   = sf_ok
        df[rover_reason]    = r_r

        # 4) HELICOPTER — survival / energy
        def heli_flags(v, has):
            if not has or pd.isna(v): return False, False, "missing"
            if v < HELI_SURVIVAL_MIN_C:   return False, False, "too_cold_survival"
            if v < HELI_ENERGY_PREF_MIN_C:return True,  False, "cold_high_energy"
            return True, True, "ok"
        surv_ok, energy_ok, h_reason = [], [], []
        for v, h in zip(df[c], df[has_col]):
            so, eo, hr = heli_flags(v, h)
            surv_ok.append(so); energy_ok.append(eo); h_reason.append(hr)
        df[heli_surv_ok]   = surv_ok
        df[heli_energy_ok] = energy_ok
        df[heli_reason]    = h_reason

        # 5) COMBINED — reason for the first veto
        def slot_strict_reason(i):
            if not df.loc[i, q_ok_col]:        return df.loc[i, q_reason_col]
            if not df.loc[i, rover_ok_strict]: return f"fail: rover({df.loc[i, rover_reason]})"
            if not df.loc[i, heli_surv_ok]:    return f"fail: heli({df.loc[i, heli_reason]})"
            return "good"

        def slot_soft_reason(i):
            if not df.loc[i, q_ok_col]:      return df.loc[i, q_reason_col]
            if not df.loc[i, rover_ok_soft]: return f"fail: rover({df.loc[i, rover_reason]})"
            if not df.loc[i, heli_surv_ok]:  return f"fail: heli({df.loc[i, heli_reason]})"
            return "good"

        df[slot_good_strict] = df[q_ok_col] & df[rover_ok_strict] & df[heli_surv_ok]
        df[slot_good_soft]   = df[q_ok_col] & df[rover_ok_soft]   & df[heli_surv_ok]
        df[slot_reason_str]  = [slot_strict_reason(i) for i in df.index]
        df[slot_reason_soft] = [slot_soft_reason(i)   for i in df.index]

    # Ordered output
    out_cols = (
        ["x","y"] + COLS +
        [f"has_{c}" for c in COLS] +
        [f"THEMIS_OK_{t}" for t in TIMES] +
        [f"THEMIS_reason_{t}" for t in TIMES] +
        [f"ROVER_OK_strict_{t}" for t in TIMES] +
        [f"ROVER_OK_soft_{t}" for t in TIMES] +
        [f"ROVER_reason_{t}" for t in TIMES] +
        [f"HELI_survival_ok_{t}" for t in TIMES] +
        [f"HELI_energy_pref_{t}" for t in TIMES] +
        [f"HELI_reason_{t}" for t in TIMES] +
        [f"SLOT_GOOD_strict_{t}" for t in TIMES] +
        [f"SLOT_REASON_strict_{t}" for t in TIMES] +
        [f"SLOT_GOOD_soft_{t}" for t in TIMES] +
        [f"SLOT_REASON_soft_{t}" for t in TIMES]
    )

    df[out_cols].to_csv(OUT_CSV, index=False)

    # Very useful summary to understand the distribution
    for t in TIMES:
        gs = df[f"SLOT_GOOD_strict_{t}"].mean()
        gf = df[f"SLOT_GOOD_soft_{t}"].mean()
        print(f"{t}: GOOD_strict={gs:.1%} | GOOD_soft={gf:.1%}  (N={len(df)})")

if __name__ == "__main__":
    main()
