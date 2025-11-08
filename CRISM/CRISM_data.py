# 1. Access mosaic data
import rasterio
import numpy as np
import os

# Define the path to the mosaic GeoTIFF file
tif_mosaic = "/content/drive/MyDrive/CRISM/Jezero/mosaic_rgb/jezero_CRISM_indices_mosaic.tif"

# Check if the file exists
if not os.path.exists(tif_mosaic):
    print(f"Errore: Il file mosaico non è stato trovato a: {tif_mosaic}")
else:
    # Open the mosaic file
    with rasterio.open(tif_mosaic) as src:
        # Read the bands (assuming order is D2300, BD2210, BD1900)
        # Remember that rasterio reads bands starting from 1
        mosaic_data = src.read([1, 2, 3]) # Read D2300, BD2210, BD1900 bands
        mosaic_transform = src.transform
        mosaic_crs = src.crs
        mosaic_width = src.width
        mosaic_height = src.height
        mosaic_nodata = src.nodata

    print(f"Dati del mosaico caricati con successo. Dimensioni: {mosaic_data.shape}")
    print(f"Trasformazione: {mosaic_transform}")
    print(f"CRS: {mosaic_crs}")
    print(f"NoData value: {mosaic_nodata}")

    # Replace nodata values with NaN for consistency in calculations
    if mosaic_nodata is not None:
        mosaic_data = np.where(mosaic_data == mosaic_nodata, np.nan, mosaic_data)

# 2. Define mesh grid, iterate, extract, calculate averages, store, and write to CSV

import pandas as pd
from rasterio.windows import from_bounds

# Assuming mosaic_data, mosaic_transform, mosaic_width, mosaic_height are available from the previous cell
# Assuming crop_xmin, crop_xmax, crop_ymin, crop_ymax are available from previous plotting cells

if 'mosaic_data' in locals() and 'mosaic_transform' in locals() and \
   'mosaic_width' in locals() and 'mosaic_height' in locals() and \
   'crop_xmin' in locals() and 'crop_xmax' in locals() and \
   'crop_ymin' in locals() and 'crop_ymax' in locals():

    # Define the number of cells in the mesh
    n_cells_x = 100
    n_cells_y = 100

    # Calculate the size of each mesh cell in EQC coordinates based on the cropped extent
    cell_width_eqc = (crop_xmax - crop_xmin) / n_cells_x
    cell_height_eqc = (crop_ymax - crop_ymin) / n_cells_y # Note: y_min and y_max order for height calculation

    results = []

    # Iterate through each mesh cell
    for i in range(n_cells_x):
        for j in range(n_cells_y):
            # Calculate the EQC bounds of the current mesh cell
            # xmin_cell = crop_xmin + i * cell_width_eqc
            # xmax_cell = crop_xmin + (i + 1) * cell_width_eqc
            # ymin_cell = crop_ymin + j * cell_height_eqc
            # ymax_cell = crop_ymin + (j + 1) * cell_height_eqc

            # Corrected calculation for cell bounds to match row/column indexing (origin='upper')
            # The top-left corner of the image is (xmin_eqc, ymax_eqc) in EQC
            # The top-left corner of the mesh starts at (crop_xmin, crop_ymax) in EQC for the first cell (0,0)
            xmin_cell_eqc = crop_xmin + i * cell_width_eqc
            xmax_cell_eqc = crop_xmin + (i + 1) * cell_width_eqc
            # For y, we start from the top (crop_ymax) and move downwards
            ymax_cell_eqc = crop_ymax - j * cell_height_eqc
            ymin_cell_eqc = crop_ymax - (j + 1) * cell_height_eqc


            # Convert EQC bounds to pixel window in the mosaic data
            try:
                # The from_bounds function expects (west, south, east, north)
                window = from_bounds(xmin_cell_eqc, ymin_cell_eqc, xmax_cell_eqc, ymax_cell_eqc, mosaic_transform)
            except Exception as e:
                print(f"Error calculating window for cell ({i}, {j}): {e}")
                continue


            # Extract pixel values within the window for each band
            # Read the data for the current window for all bands
            try:
                cell_data = mosaic_data[:, int(window.row_off):int(window.row_off + window.height),
                                        int(window.col_off):int(window.col_off + window.width)]
            except IndexError:
                # This can happen if the calculated window is outside the mosaic dimensions
                # In this case, the cell is outside the data coverage, so we'll have NaN values
                cell_data = np.full((3, int(window.height), int(window.width)), np.nan)
            except Exception as e:
                print(f"Error extracting data for cell ({i}, {j}): {e}")
                cell_data = np.full((3, int(window.height), int(window.width)), np.nan)


            # Calculate average non-NaN value for each band in the cell
            # Bands are assumed to be D2300, BD2210, BD1900
            avg_d2300 = np.nanmean(cell_data[0, :, :])
            avg_bd2210 = np.nanmean(cell_data[1, :, :])
            avg_bd1900 = np.nanmean(cell_data[2, :, :])

            # Append the results for the current cell
            results.append({'x': i,
                            'y': j,
                            'Avg_D2300': avg_d2300,
                            'Avg_BD2210': avg_bd2210,
                            'Avg_BD1900': avg_bd1900})

    # Create a pandas DataFrame from the results
    df_results = pd.DataFrame(results)

    # Replace NaN values with 0 as requested by the user
    df_results = df_results.fillna(0)

    # Define the output CSV path
    output_csv_path = os.path.join(OUT_DIR, "mesh_mineral_averages.csv")

    # Write the DataFrame to a CSV file
    df_results.to_csv(output_csv_path, index=False)

# Show the shape of the df_results DataFrame
if 'df_results' in locals():
    print(f"Shape of df_results: {df_results.shape}")
else:
    print("Errore: La variabile 'df_results' non è stata trovata. Assicurati di aver eseguito la cella che crea il DataFrame.")

    print(f"✅ File CSV creato con successo: {output_csv_path}")
    display(df_results.head())

else:
    print("Errore: Variabili del mosaico o di ritaglio non trovate. Assicurati di aver eseguito le celle precedenti.")

# 3. Ensure the DataFrame df_results with average mineral index values per mesh cell is available.
import pandas as pd
import os

# Check if df_results exists
if 'df_results' not in locals():
    output_csv_path = os.path.join(OUT_DIR, "mesh_mineral_averages.csv")
    if os.path.exists(output_csv_path):
        df_results = pd.read_csv(output_csv_path)
        print("DataFrame 'df_results' loaded from CSV.")
    else:
        print(f"Error: CSV file not found at {output_csv_path}. Cannot proceed with the subtask.")
else:
    print("DataFrame 'df_results' already exists.")

# Display the head of the DataFrame if it exists
if 'df_results' in locals():
    display(df_results.head())

# Calculate minimum and maximum values for each mineral index
min_d2300 = df_results['Avg_D2300'].min()
max_d2300 = df_results['Avg_D2300'].max()

min_bd2210 = df_results['Avg_BD2210'].min()
max_bd2210 = df_results['Avg_BD2210'].max()

min_bd1900 = df_results['Avg_BD1900'].min()
max_bd1900 = df_results['Avg_BD1900'].max()

print(f"Min Avg_D2300: {min_d2300}, Max Avg_D2300: {max_d2300}")
print(f"Min Avg_BD2210: {min_bd2210}, Max Avg_BD2210: {max_bd2210}")
print(f"Min Avg_BD1900: {min_bd1900}, Max Avg_BD1900: {max_bd1900}")
