# This cell loads the operational flags CSV and generates a new CSV file ('themis_ml_flags_only.csv') for machine learning, 
# which unifies the strict and soft operational status flags into single columns per fascia.
import pandas as pd

# Input file from previous steps
IN_FLAGS_CSV = "themis_timeslot_flags_ops.csv"
# Output file for ML colleague
OUT_ML_FLAGS_CSV = "themis_ml_flags_only.csv"

TIMES = ["5_30AM","7_00AM","6_30PM","7_00PM"]

try:
    df_flags_ops = pd.read_csv(IN_FLAGS_CSV)
except FileNotFoundError:
    print(f"[ERROR] File '{IN_FLAGS_CSV}' non trovato. Assicurati di aver eseguito la cella che lo genera.")
    exit()

# Prepare a new DataFrame for the unified flags
df_ml_flags_unified = pd.DataFrame({'x': df_flags_ops['x'], 'y': df_flags_ops['y']})

for t in TIMES:
    good_strict_col = f"SLOT_GOOD_strict_{t}"
    reason_strict_col = f"SLOT_REASON_strict_{t}"
    status_strict_col = f"SLOT_STATUS_strict_{t}"

    good_soft_col = f"SLOT_GOOD_soft_{t}"
    reason_soft_col = f"SLOT_REASON_soft_{t}"
    status_soft_col = f"SLOT_STATUS_soft_{t}"

    if good_strict_col in df_flags_ops.columns and reason_strict_col in df_flags_ops.columns:
        df_ml_flags_unified[status_strict_col] = df_flags_ops.apply(
            lambda row: "True" if row[good_strict_col] else f"Fail: {row[reason_strict_col]}",
            axis=1
        )
    else:
        print(f"[WARN] Colonne strict per la fascia {t} non trovate: {good_strict_col} o {reason_strict_col}")
        df_ml_flags_unified[status_strict_col] = "Missing_Data"

    if good_soft_col in df_flags_ops.columns and reason_soft_col in df_flags_ops.columns:
        df_ml_flags_unified[status_soft_col] = df_flags_ops.apply(
            lambda row: "True" if row[good_soft_col] else f"Fail: {row[reason_soft_col]}",
            axis=1
        )
    else:
        print(f"[WARN] Colonne soft per la fascia {t} non trovate: {good_soft_col} o {reason_soft_col}")
        df_ml_flags_unified[status_soft_col] = "Missing_Data"

# Save to the new CSV file
df_ml_flags_unified.to_csv(OUT_ML_FLAGS_CSV, index=False)

print(f"File CSV per Machine Learning salvato in: {OUT_ML_FLAGS_CSV}")
print("Prime 5 righe del nuovo file CSV:")
display(df_ml_flags_unified.head())
