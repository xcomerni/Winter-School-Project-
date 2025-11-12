import matplotlib.pyplot as plt
import rasterio
import numpy as np

# Ensure png_quicklook is defined, it should be from the previous cell's execution
# If running this cell independently, ensure png_quicklook and its dependencies are available
# (e.g., MARS_R, math, Affine, CRS from rasterio.crs and rasterio.transform)

# Re-define png_quicklook function in this cell for self-containment
def png_quicklook(arr, transform, lon0, out_png, title, vmin=None, vmax=None, cmap="inferno", cbar_label="Temperature (K)"):
    m = np.isfinite(arr)
    if not m.any():
        print("[warn] PNG saltata:", title); return
    
    # Use provided vmin/vmax for consistent scaling, fallback to percentiles if not provided
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
    # Pass vmin and vmax directly to imshow for consistent scaling
    im = plt.imshow(arr, cmap=cmap, origin="upper", extent=[lonL,lonR,latB,latT], vmin=lo, vmax=hi)
    plt.xlabel("Longitude (°E)"); plt.ylabel("Latitude (°N)")
    plt.title(title); plt.grid(alpha=0.3); plt.tight_layout()
    plt.colorbar(im, label=cbar_label) # Add colorbar with label
    plt.savefig(out_png, dpi=200); plt.close()
    print("PNG:", out_png)

# Ensure essential variables are available (assuming previous cell ran)
if 'fasce_data' not in globals() or 'dst_tf' not in globals() or 'lon0' not in globals() or \
   'global_lo' not in globals() or 'global_hi' not in globals() or 'fascia_times' not in globals() or 'BBOX_DEG' not in globals() or 'MARS_R' not in globals():
    print("[ERROR] Variabili necessarie per il plotting non trovate. Assicurati di aver eseguito la cella precedente.")
else:
    for nome, data in fasce_data.items():
        bt = data["bt"]

        # Get the time string and sanitize it for filename
        time_str = fascia_times.get(nome, "Unknown_Time").replace(" ", "").replace(":", "_")
        png_bt   = f"/content/themis_BT_{time_str}_median.png"
        
        # Generate the new title using the fascia_times dictionary
        title = f"THEMIS - Median at {fascia_times.get(nome, 'Unknown Time')}"
        png_quicklook(bt, dst_tf, lon0, png_bt, title, vmin=global_lo, vmax=global_hi)

    print("Generazione PNG completata.")
