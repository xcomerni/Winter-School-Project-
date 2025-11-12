import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Assuming OUT_DIR is defined from previous cells
output_csv_path_updated = os.path.join(OUT_DIR, "mesh_mineral_averages_percentages.csv")

# Ensure the DataFrame is loaded
if 'df' not in locals() or df.empty:
    try:
        df = pd.read_csv(output_csv_path_updated)
    except FileNotFoundError:
        print(f"Error: The file {output_csv_path_updated} was not found.")
        print("Please ensure the previous steps for saving the CSV were executed correctly.")
        # Exit or handle the error appropriately
        raise SystemExit("Missing CSV file.")

# 1) Gating: if the row has all zero -> avoid it
df["crism_has_data"] = (df[["Avg_D2300","Avg_BD2210","Avg_BD1900"]].sum(axis=1) > 0)

# 2) Weights: “water-first”
w_H2O, w_FeMg, w_AlOH = 0.60, 0.30, 0.10

# 3) Weighted score (0–100)
df["CRISM_score"] = (w_H2O*df["% H2O"] +
                     w_FeMg*df["% Fe/Mg"] +
                     w_AlOH*df["% Al-OH"])

# 4B) Adaptive thresholds (recommended): use the quantiles of your dataset
Q = df.loc[df["crism_has_data"], ["% H2O","% Fe/Mg","% Al-OH"]].quantile([0.6, 0.8]).rename(
    index={0.6:"p60", 0.8:"p80"}
)
df["CRISM_OK_quantile"] = (
    df["crism_has_data"] &
    (
        (df["% H2O"] >= Q.loc["p80","% H2O"]) |                                   # top 20% H2O
        ((df["% H2O"] >= Q.loc["p60","% H2O"]) & (df["% Fe/Mg"] >= Q.loc["p60","% Fe/Mg"]))
    ) &
    (df["CRISM_score"] >= (0.55*Q.loc["p80","% H2O"] + 0.45*Q.loc["p60","% Fe/Mg"]))
)

import matplotlib.pyplot as plt
import seaborn as sns
import os

# Ensure df is loaded and CRISM_score is calculated
# If df is not in locals, load it first and re-calculate necessary columns
if 'df' not in locals() or df.empty or 'CRISM_score' not in df.columns:
    output_csv_path_updated = os.path.join(OUT_DIR, "mesh_mineral_averages_percentages.csv")
    try:
        df = pd.read_csv(output_csv_path_updated)
        df["crism_has_data"] = (df[["Avg_D2300","Avg_BD2210","Avg_BD1900"]].sum(axis=1) > 0)
        w_H2O, w_FeMg, w_AlOH = 0.60, 0.30, 0.10
        df["CRISM_score"] = (w_H2O*df["% H2O"] + w_FeMg*df["% Fe/Mg"] + w_AlOH*df["% Al-OH"])
        
        # Re-calculate CRISM_OK_quantile in case the DataFrame was reloaded
        Q = df.loc[df["crism_has_data"], ["% H2O","% Fe/Mg","% Al-OH"]].quantile([0.6, 0.8]).rename(
            index={0.6:"p60", 0.8:"p80"}
        )
        df["CRISM_OK_quantile"] = (
            df["crism_has_data"] &
            (
                (df["% H2O"] >= Q.loc["p80","% H2O"]) |                                   # top 20% H2O
                ((df["% H2O"] >= Q.loc["p60","% H2O"]) & (df["% Fe/Mg"] >= Q.loc["p60","% Fe/Mg"]))
            ) &
            (df["CRISM_score"] >= (0.55*Q.loc["p80","% H2O"] + 0.45*Q.loc["p60","% Fe/Mg"]))
        )

    except FileNotFoundError:
        print(f"Error: The file {output_csv_path_updated} was not found.")
        print("Please ensure the previous steps for saving the CSV were executed correctly.")
        raise SystemExit("Missing CSV file.")

# Filter out rows where there is no CRISM data (all original averages were 0)
df_crism_data = df[df['crism_has_data']].copy()

if df_crism_data.empty:
    print("No cells with valid CRISM data found to plot the score distribution.")
else:
    plt.figure(figsize=(10, 6))
    sns.histplot(data=df_crism_data, x='CRISM_score', bins=20, kde=True, color='darkgreen')
    plt.title('Distribution of CRISM Score (Cells with Data - Quantile Method)')
    plt.xlabel('CRISM Score')
    plt.ylabel('Number of Mesh Cells')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()

    # Save the plot
    score_quantile_hist_path = os.path.join(OUT_DIR, "crism_score_distribution_quantile_histogram.png")
    plt.savefig(score_quantile_hist_path)
    print(f"✅ CRISM Score (Quantile) distribution histogram saved to: {score_quantile_hist_path}")

    plt.show()
