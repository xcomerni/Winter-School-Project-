# Coverage Maps for each band (e.g., /content/themis_Coverage_5_30AM.png),
# showing the data density in each area.
# A Difference Map (/content/themis_Diff_7_00PM_vs_5_30AM.png),
# illustrating the temperature variation between the evening band (7:00 PM) and the morning one (5:30 AM).

import matplotlib.pyplot as plt
import rasterio
import numpy as np

# Re-define png_quicklook function for self-containment in this cell
def png_quicklook(arr, transform, lon0, out_png, title, vmin=None, vmax=None, cmap="inferno", cbar_label="Temperature (K)"):
    m = np.isfinite(arr)
    if not m.any():
        print("[warn] PNG skipped:", title); return
    
    if vmin is None or vmax is None:
        lo, hi = np.percentile(arr[m],[2,98]); hi=max(hi, lo+1e-6)
    else:
        lo, hi = vmin, vmax

    H,W = arr.shape
    x0,y0 = transform.c, transform.f
    x1 = x0 + transform.a*W; y1 = y0 + transform.e*H
    lonL = lon0 + (np.degrees(x0/MARS_R) if 'MARS_R' in globals() else 0); lonR = lon0 + (np.degrees(x1/MARS_R) if 'MARS_R' in globals() else 0)
    latB = (np.degrees(y1/MARS_R) if 'MARS_R' in globals() else 0);       latT = (np.degrees(y0/MARS_R) if 'MARS_R' in globals() else 0)
    
    plt.figure(figsize=(8,6), dpi=140)
    im = plt.imshow(arr, cmap=cmap, origin="upper", extent=[lonL,lonR,latB,latT], vmin=lo, vmax=hi)
    plt.xlabel("Longitude (°E)"); plt.ylabel("Latitude (°N)")
    plt.title(title); plt.grid(alpha=0.3); plt.tight_layout()
    plt.colorbar(im, label=cbar_label)
    plt.savefig(out_png, dpi=200); plt.close()
    print("PNG:", out_png)

# Ensure essential variables are available (assuming previous cell ran)
if 'fasce_data' not in globals() or 'dst_tf' not in globals() or 'lon0' not in globals() or \
   'fascia_times' not in globals() or 'BBOX_DEG' not in globals() or 'MARS_R' not in globals():
    print("[ERROR] Variables required for plotting not found. Make sure you ran the previous cell.")
else:
    # 1. Generate Coverage Count Maps for each band
    print("\n--- Generating Coverage Maps ---")
    for nome, data in fasce_data.items():
        cnt = data["cnt"]
        time_str = fascia_times.get(nome, "Unknown_Time").replace(" ", "").replace(":", "_")
        png_cnt = f"/content/themis_Coverage_{time_str}.png"
        title = f"THEMIS - Coverage Count at {fascia_times.get(nome, 'Unknown Time')}"
        # Use a discrete colormap for counts, vmin=0, vmax=maximum count
        max_count = np.max([np.max(f_data['cnt'][np.isfinite(f_data['cnt'])]) for f_data in fasce_data.values()])
        png_quicklook(cnt, dst_tf, lon0, png_cnt, title, vmin=0, vmax=max_count, cmap="viridis", cbar_label="Number of Images")
    
    # 2. Generate Difference Maps between bands
    print("\n--- Generating Difference Maps ---")
    # Example: Difference between evening (band 3) and morning (band 1)
    if "fascia_3" in fasce_data and "fascia_1" in fasce_data:
        bt_fascia_3 = fasce_data["fascia_3"]["bt"]
        bt_fascia_1 = fasce_data["fascia_1"]["bt"]
        
        # Calculate difference, handling NaNs
        diff_3_1 = bt_fascia_3 - bt_fascia_1
        diff_mask = np.isfinite(diff_3_1)
        
        if diff_mask.any():
            # Determine a symmetric color scale for differences
            max_abs_diff = np.max(np.abs(diff_3_1[diff_mask]))
            diff_vmin = -max_abs_diff
            diff_vmax = max_abs_diff
            
            time_str_3 = fascia_times.get("fascia_3", "Unknown_Time").replace(" ", "").replace(":", "_")
            time_str_1 = fascia_times.get("fascia_1", "Unknown_Time").replace(" ", "").replace(":", "_")
            
            png_diff = f"/content/themis_Diff_{time_str_3}_vs_{time_str_1}.png"
            title = f"THEMIS - Temperature Difference: {fascia_times.get('fascia_3')} - {fascia_times.get('fascia_1')}"
            
            png_quicklook(diff_3_1, dst_tf, lon0, png_diff, title,
                          vmin=diff_vmin, vmax=diff_vmax, cmap="RdBu_r", cbar_label="Temperature Difference (K)")
        else:
            print("[warn] Unable to calculate the difference between band_3 and band_1: no valid data.")
    else:
        print("[warn] Bands 1 or 3 not found for difference calculation.")

    print("Additional plots generation completed.")
