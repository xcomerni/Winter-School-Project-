# Four histograms (/content/themis_TempHist_Grid100x100_*.png), one for each time band, 
# showing the distribution of detected temperatures on the 100x100 grid.
# A bar chart (/content/themis_MeanTemp_Grid100x100_BarChart.png), comparing 
# the average temperatures across different bands, based on the same grid data.

import matplotlib.pyplot as plt
import rasterio
import numpy as np
import pandas as pd # Needed for DataFrame operations like mean()

# Ensure essential variables are available (assuming previous cells ran)
if 'fasce_data' not in globals() or 'fascia_times' not in globals():
    print("[ERROR] Variables required for the plots not found. Make sure you ran the previous cells.")
else:
    print("\n--- Generating Temperature Histograms ---")
    all_fascia_means = []

    for nome, data in fasce_data.items():
        time_str_raw = fascia_times.get(nome, "Unknown Time")
        time_str_file = time_str_raw.replace(" ", "").replace(":", "_")
        
        # Load data from the 100x100 aggregated TIFF file
        tif_grid_path = f"/content/themis_BT_Grid100x100_{time_str_file}_median.tif"
        
        try:
            with rasterio.open(tif_grid_path) as src:
                bt_data_aggregated = src.read(1)  # Read aggregated temperature data
                bt_data_aggregated[bt_data_aggregated == src.nodata] = np.nan # Replace nodata with NaN
            
            # Flatten the array and remove NaN values for the histogram
            valid_temperatures = bt_data_aggregated[np.isfinite(bt_data_aggregated)]

            if valid_temperatures.size > 0:
                plt.figure(figsize=(8, 5), dpi=140)
                plt.hist(valid_temperatures, bins=50, color='skyblue', edgecolor='black')
                plt.title(f'Temperature Distribution (100x100 Grid) - {time_str_raw}')
                plt.xlabel('Temperature (K)')
                plt.ylabel('Frequency (Number of Pixels)') 
                plt.grid(axis='y', alpha=0.75)
                plt.tight_layout()
                png_hist = f"/content/themis_TempHist_Grid100x100_{time_str_file}.png"
                plt.savefig(png_hist, dpi=200)
                plt.close()
                print("PNG:", png_hist)

                # Store mean temperature for the bar chart
                all_fascia_means.append({'Band': time_str_raw, 'Mean Temperature (K)': np.mean(valid_temperatures)})
            else:
                print(f"[warn] No valid temperature data for histogram in {time_str_raw}")
        except FileNotFoundError:
            print(f"[warn] File {tif_grid_path} not found. Make sure you executed the 100x100 grid generation cell.")
        except Exception as e:
            print(f"[ERROR] Error while processing {tif_grid_path}: {e}")

    print("\n--- Generating Bar Chart of Mean Temperatures ---")
    if all_fascia_means:
        df_fascia_means = pd.DataFrame(all_fascia_means)
        df_fascia_means = df_fascia_means.sort_values(by='Band')

        plt.figure(figsize=(10, 6), dpi=140)
        plt.bar(df_fascia_means['Band'], df_fascia_means['Mean Temperature (K)'], color='lightcoral')
        plt.title('Mean Temperature (100x100 Grid)')
        plt.xlabel('Hour (hh:mm)')
        plt.ylabel('Mean Temperature (K)')
        plt.grid(axis='y', alpha=0.75)
        plt.tight_layout()
        png_barchart = "/content/themis_MeanTemp_Grid100x100_BarChart.png"
        plt.savefig(png_barchart, dpi=200)
        plt.close()
        print("PNG:", png_barchart)
    else:
        print("[warn] No data to generate the mean temperature bar chart.")

    print("Summary plots generation completed.")
