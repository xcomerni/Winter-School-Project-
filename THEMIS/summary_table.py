# This cell loads the operational flags CSV and generates a summary table of 'Good' and 'Bad' slots for each time fascia.
import pandas as pd

OUT_CSV = "themis_timeslot_flags_ops.csv"
TIMES = ["5_30AM","7_00AM","6_30PM","7_00PM"]

try:
    df_flags_ops = pd.read_csv(OUT_CSV)
except FileNotFoundError:
    print(f"[ERROR] File '{OUT_CSV}' non trovato. Assicurati di aver eseguito la cella che lo genera.")
    exit()

summary_data = []

for t in TIMES:
    good_strict_col = f"SLOT_GOOD_strict_{t}"
    good_soft_col = f"SLOT_GOOD_soft_{t}"

    if good_strict_col in df_flags_ops.columns and good_soft_col in df_flags_ops.columns:
        good_strict_count = df_flags_ops[good_strict_col].sum()
        good_soft_count = df_flags_ops[good_soft_col].sum()
        total_slots = len(df_flags_ops)
        bad_strict_count = total_slots - good_strict_count
        bad_soft_count = total_slots - good_soft_count

        summary_data.append({
            "Fascia Oraria": t,
            "Good (Strict)": int(good_strict_count),
            "Bad (Strict)": int(bad_strict_count),
            "Good (Soft)": int(good_soft_count),
            "Bad (Soft)": int(bad_soft_count),
            "Totale Slot": total_slots
        })
    else:
        print(f"[WARN] Colonne per la fascia {t} non trovate: {good_strict_col} o {good_soft_col}")

if summary_data:
    summary_df = pd.DataFrame(summary_data)
    print("\nRiassunto delle Flag per Fascia Oraria:")
    display(summary_df)
else:
    print("Nessun dato di riepilogo disponibile.")
