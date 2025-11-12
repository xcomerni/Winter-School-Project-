# This cell generates 100x100 aggregated temperature maps from median TIFs.
# It calculates block averages and saves the results as GeoTIFFs and PNGs.
import matplotlib.pyplot as plt
import rasterio
import numpy as np

# Re-define a plotting function suitable for generic grid heatmaps with numerical axes
def plot_grid_heatmap(arr, out_png, title, vmin=None, vmax=None, cmap="inferno", cbar_label="Value"):
    grid_H, grid_W = arr.shape
    plt.figure(figsize=(10, 8), dpi=140)

    # Use imshow to display the 2D array. extent will map the array indices to axis ranges.
    # For 100x100 grid, indices are 0-99. We want labels 1-100.
    # Using extent=[0, grid_W, grid_H, 0] makes the axes run from 0 to 100.
    im = plt.imshow(arr, cmap=cmap, origin="upper", vmin=vmin, vmax=vmax, extent=[0, grid_W, grid_H, 0])

    plt.title(title)
    plt.xlabel('Grid Column')
    plt.ylabel('Grid Row')

    # Set ticks and labels for 1-100 on the axes
    # Ticks are placed at the start of each major block (e.g., 10, 20, ...) for readability
    # Minor ticks for every cell can be added for a grid effect.
    plt.xticks(np.arange(0, grid_W + 1, 10))
    plt.yticks(np.arange(0, grid_H + 1, 10))

    # Optional: Add minor grid lines for every cell
    plt.gca().set_xticks(np.arange(0.5, grid_W, 1), minor=True)
    plt.gca().set_yticks(np.arange(0.5, grid_H, 1), minor=True)
    plt.grid(which='minor', color='w', linestyle='-', linewidth=0.5)
    plt.grid(which='major', color='k', linestyle='-', linewidth=1)

    plt.colorbar(im, label=cbar_label)
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.close()
    print("PNG:", out_png)

# Ensure essential variables are available from previous cells
if 'fasce_data' not in globals() or 'fascia_times' not in globals() or \
   'global_lo' not in globals() or 'global_hi' not in globals() or 'dst_tf' not in globals() or 'dst_crs' not in globals():
    print("[ERROR] Variabili necessarie per il plotting non trovate. Assicurati di aver eseguito le celle precedenti.")
else:
    print("\n--- Generazione Mappe di Temperatura Aggregate (100x100) ---")

    target_grid_size = 100

    for nome, data in fasce_data.items():
        time_str_raw = fascia_times.get(nome, "Unknown Time")
        time_str_file = time_str_raw.replace(" ", "").replace(":", "_")
        tif_file_path = f"/content/themis_BT_{time_str_file}_median.tif"

        try:
            with rasterio.open(tif_file_path) as src:
                bt_data = src.read(1)  # Read the temperature data
                bt_data[bt_data == src.nodata] = np.nan # Replace nodata with NaN

            H_orig, W_orig = bt_data.shape

            # Calculate block sizes for averaging
            block_h = H_orig // target_grid_size
            block_w = W_orig // target_grid_size

            # Create an empty array for the aggregated grid
            aggregated_bt = np.full((target_grid_size, target_grid_size), np.nan, dtype=np.float32)

            # Perform block averaging
            for i in range(target_grid_size):
                for j in range(target_grid_size):
                    h_start = i * block_h
                    h_end = (i + 1) * block_h
                    w_start = j * block_w
                    w_end = (j + 1) * block_w

                    # Adjust end points for the last row/column to include all pixels
                    if i == target_grid_size - 1:
                        h_end = H_orig
                    if j == target_grid_size - 1:
                        w_end = W_orig

                    block_data = bt_data[h_start:h_end, w_start:w_end]
                    valid_block_data = block_data[np.isfinite(block_data)]

                    if valid_block_data.size > 0:
                        aggregated_bt[i, j] = np.mean(valid_block_data)

            # Define filename for the aggregated TIFF
            tif_grid_path = f"/content/themis_BT_Grid100x100_{time_str_file}_median.tif"
            
            # Save the aggregated data to a TIFF file
            save_tif(tif_grid_path, aggregated_bt, dst_tf, dst_crs)

            # Plot the aggregated grid
            png_grid = f"/content/themis_BT_Grid100x100_{time_str_file}_median.png"
            title = f"THEMIS - 100x100 Grid Median Temp at {time_str_raw}"
            plot_grid_heatmap(aggregated_bt, png_grid, title, vmin=global_lo, vmax=global_hi, cbar_label="Temperature (K)")

        except FileNotFoundError:
            print(f"[warn] File {tif_file_path} non trovato. Assicurati di aver eseguito la cella di elaborazione principale.")
        except Exception as e:
            print(f"[ERROR] Errore durante l'elaborazione di {tif_file_path}: {e}")

    print("Generazione delle mappe di temperatura aggregate completata.")
