import pandas as pd
import numpy as np
import rasterio
import os

# Ensure fascia_times is defined (it should be from previous cells)
# For robustness, redefine if not in globals, though it should be.
if 'fascia_times' not in globals():
    fascia_times = {
        "fascia_1": "5:30 AM",
        "fascia_2": "7:00 AM",
        "fascia_3": "7:00 PM",
        "fascia_4": "6:30 PM",
    }

dataframes_to_merge = []

# Assuming target_grid_size is 100 from previous cell's execution
# If not explicitly in globals, default it
if 'target_grid_size' not in globals():
    target_grid_size = 100

for nome, time_raw in fascia_times.items():
    time_str_file = time_raw.replace(" ", "").replace(":", "_")
    tif_grid_path = f"/content/themis_BT_Grid100x100_{time_str_file}_median.tif"

    try:
        with rasterio.open(tif_grid_path) as src:
            aggregated_bt = src.read(1)
            # Replace nodata with NaN, as it's typically how missing values are handled in analysis
            aggregated_bt[aggregated_bt == src.nodata] = np.nan

        # Create x, y coordinates for the 100x100 grid (0-indexed)
        y_coords, x_coords = np.indices(aggregated_bt.shape) # y_coords for rows, x_coords for columns

        temp_df = pd.DataFrame({
            'x': x_coords.flatten(),
            'y': y_coords.flatten(),
            f'mean_temperature_{time_str_file}': aggregated_bt.flatten()
        })
        dataframes_to_merge.append(temp_df)

    except FileNotFoundError:
        print(f"[ERROR] File '{tif_grid_path}' non trovato. Assicurati di aver generato i file della griglia 100x100.")
    except Exception as e:
        print(f"[ERROR] Errore durante il caricamento o l'elaborazione di '{tif_grid_path}': {e}")

if not dataframes_to_merge:
    raise SystemExit("Nessun dato aggregato 100x100 trovato per la creazione del CSV ML. Impossibile creare il file CSV.")

# Merge all dataframes on 'x' and 'y' coordinates
final_ml_df = dataframes_to_merge[0]
for i in range(1, len(dataframes_to_merge)):
    final_ml_df = pd.merge(final_ml_df, dataframes_to_merge[i], on=['x', 'y'], how='outer')

# Sort by y and x for consistent output (matches image indexing from top-left)
final_ml_df = final_ml_df.sort_values(by=['y', 'x']).reset_index(drop=True)

# Save to CSV
output_csv_path = "/content/themis_ML_data_100x100.csv"
final_ml_df.to_csv(output_csv_path, index=False)

print(f"File CSV per Machine Learning salvato in: {output_csv_path}")
print("Prime 5 righe del file CSV:")
display(final_ml_df.head())
