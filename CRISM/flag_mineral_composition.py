import os
import pandas as pd

# Ensure df is loaded and CRISM_OK_quantile is calculated
# This block is a safeguard; it reloads and recalculates if 'df' is not in locals or missing columns
if 'df' not in locals() or df.empty or 'CRISM_OK_quantile' not in df.columns:
    output_csv_path_updated = os.path.join(OUT_DIR, "mesh_mineral_averages_percentages.csv")
    try:
        df = pd.read_csv(output_csv_path_updated)
        df["crism_has_data"] = (df[["Avg_D2300","Avg_BD2210","Avg_BD1900"]].sum(axis=1) > 0)
        w_H2O, w_FeMg, w_AlOH = 0.60, 0.30, 0.10
        df["CRISM_score"] = (w_H2O*df["% H2O"] + w_FeMg*df["% Fe/Mg"] + w_AlOH*df["% Al-OH"])
        
        # Recalculate CRISM_OK_quantile
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

# Create the DataFrame for the machine learning model
# Select 'x' and 'y' (pixel positions) and convert 'CRISM_OK_quantile' to an integer flag
df_ml = df[['x', 'y']].copy()
df_ml['landing_flag'] = df['CRISM_OK_quantile'].astype(int) # True becomes 1, False becomes 0

# Define the output path for the new CSV
output_ml_csv_path = os.path.join(OUT_DIR, "crism_landing_flags_quantile.csv")

# Save the DataFrame to a CSV file
df_ml.to_csv(output_ml_csv_path, index=False)

print(f"✅ CSV for machine learning model successfully created: {output_ml_csv_path}")
display(df_ml.head())


good_spots = df_ml['landing_flag'].sum()
bad_spots = len(df_ml) - good_spots

print(f"Number of good landing spots (landing_flag = 1): {good_spots}")
print(f"Number of bad landing spots (landing_flag = 0): {bad_spots}")



import matplotlib.pyplot as plt
import pandas as pd
import os

# Ensure df is loaded and CRISM_OK_quantile is calculated
if 'df' not in locals() or df.empty or 'CRISM_OK_quantile' not in df.columns:
    output_csv_path_updated = os.path.join(OUT_DIR, "mesh_mineral_averages_percentages.csv")
    try:
        df = pd.read_csv(output_csv_path_updated)
        df["crism_has_data"] = (df[["Avg_D2300","Avg_BD2210","Avg_BD1900"]].sum(axis=1) > 0)
        w_H2O, w_FeMg, w_AlOH = 0.60, 0.30, 0.10
        df["CRISM_score"] = (w_H2O*df["% H2O"] + w_FeMg*df["% Fe/Mg"] + w_AlOH*df["% Al-OH"])
        
        Q = df.loc[df["crism_has_data"], ["% H2O","% Fe/Mg","% Al-OH"]].quantile([0.6, 0.8]).rename(
            index={0.6:"p60", 0.8:"p80"}
        )
        df["CRISM_OK_quantile"] = (
            df["crism_has_data"] &
            (
                (df["% H2O"] >= Q.loc["p80","% H2O"]) |                                   
                ((df["% H2O"] >= Q.loc["p60","% H2O"]) & (df["% Fe/Mg"] >= Q.loc["p60","% Fe/Mg"]))
            ) &
            (df["CRISM_score"] >= (0.55*Q.loc["p80","% H2O"] + 0.45*Q.loc["p60","% Fe/Mg"]))
        )
    except FileNotFoundError:
        print(f"Error: The file {output_csv_path_updated} was not found.")
        print("Please ensure the previous steps for saving the CSV were executed correctly.")
        raise SystemExit("Missing CSV file.")

# Filter for good landing spots based on CRISM_OK_quantile
df_good_spots = df[df['CRISM_OK_quantile'] == True].copy()

if df_good_spots.empty:
    print("No good landing spots found based on CRISM_OK_quantile criteria. Cannot analyze mineral composition.")
else:
    # Calculate the average percentage of each mineral for good landing spots
    avg_fe_mg_good = df_good_spots['% Fe/Mg'].mean()
    avg_al_oh_good = df_good_spots['% Al-OH'].mean()
    avg_h2o_good = df_good_spots['% H2O'].mean()

    print("Average Mineral Composition for Good Landing Spots:")
    print(f"  % Fe/Mg Smectite: {avg_fe_mg_good:.2f}%")
    print(f"  % Al-OH Minerals: {avg_al_oh_good:.2f}%")
    print(f"  % H2O / Hydrated Silica: {avg_h2o_good:.2f}%")

    # Prepare data for pie chart
    proportions = [avg_fe_mg_good, avg_al_oh_good, avg_h2o_good]
    labels = ['Fe/Mg Smectite', 'Al-OH Minerals', 'H2O / Hydrated Silica']
    colors = ['red', 'green', 'blue'] # Consistent with RGB assignment

    # Create the pie chart
    fig, ax = plt.subplots(figsize=(10, 8))
    wedges, texts, autotexts = ax.pie(proportions, colors=colors, autopct='%1.1f%%', startangle=90, pctdistance=0.85)

    ax.axis('equal')
    ax.set_title('Average Mineral Composition in Good Landing Spots (CRISM Quantile)')

    # Add legend with colored rectangles
    from matplotlib.patches import Rectangle # Ensure Rectangle is imported if not already
    legend_handles = [Rectangle((0, 0), 1, 1, color=c, ec="k") for c in colors]
    ax.legend(legend_handles, labels, loc='center left', bbox_to_anchor=(1.02, 0.5))

    # Define output path for pie chart
    pie_chart_good_spots_path = os.path.join(OUT_DIR, "good_landing_spots_mineral_composition_pie_chart.png")
    plt.savefig(pie_chart_good_spots_path, bbox_inches='tight', pad_inches=0.1)
    print(f"✅ Pie chart of good landing spots mineral composition saved to: {pie_chart_good_spots_path}")

    plt.show()
