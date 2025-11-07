# mola_slope_roughness.py
import os
import re
import numpy as np
from osgeo import gdal
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import from_bounds
from scipy.ndimage import generic_filter
import matplotlib.pyplot as plt
import csv

# -----------------------
# USER CONFIG
# -----------------------
DATA_FOLDER = r"C:\Users\zuzia\Documents\GitHub\Winter-School-Project-\MOLA"
# Label file for the topography product 
LBL_FILENAME = "megt44n000hb.lbl"
IMG_FILENAME = "megt44n000hb.img"

# Output names (will be written into DATA_FOLDER)
OUT_TOPO_TIF = "mola_topography.tif"
OUT_SLOPE_TIF = "mola_slope_deg.tif"

# -----------------------
# Helpers
# -----------------------
def read_label_map_scale_km(lbl_path):
    """Parse MAP_SCALE value (KM/PIXEL) from a PDS3 .lbl file. Returns meters/pixel."""
    with open(lbl_path, 'r', encoding='utf-8', errors='ignore') as fh:
        txt = fh.read()
    # Remove newlines and extra spaces for easier regex matching
    txt_flat = re.sub(r'[\r\n]+', ' ', txt)
    txt_flat = re.sub(r'\s+', ' ', txt_flat)
    # Debug: print a snippet to help diagnose
    print("[DEBUG] First 500 chars of label:", txt_flat[:500])
    # look for MAP_SCALE = 3.705 <KM/PIXEL> (case-insensitive)
    m = re.search(r"MAP_SCALE\s*=\s*([0-9]*\.?[0-9]+)\s*<\s*KM\s*/\s*PIXEL\s*>", txt_flat, re.IGNORECASE)
    if m:
        km_per_pixel = float(m.group(1))
        print(f"[DEBUG] Found MAP_SCALE: {km_per_pixel} KM/PIXEL")
        return km_per_pixel * 1000.0
    # fallback: try MAP_RESOLUTION -> pixels/degree and approximate with mean metres per degree
    m2 = re.search(r"MAP_RESOLUTION\s*=\s*([0-9]*\.?[0-9]+)\s*<\s*PIXEL\s*/\s*DEGREE\s*>", txt_flat, re.IGNORECASE)
    if m2:
        pix_per_deg = float(m2.group(1))
        print(f"[DEBUG] Found MAP_RESOLUTION: {pix_per_deg} PIXEL/DEGREE")
        meters_per_deg = 59200.0
        deg_per_pix = 1.0 / pix_per_deg
        return deg_per_pix * meters_per_deg
    raise RuntimeError("Could not parse MAP_SCALE or MAP_RESOLUTION from label file.\nLabel snippet:\n" + txt_flat[:500])

def ensure_file_exists(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Required file not found: {path}")

# -----------------------
# 0. Check files exist
# -----------------------
lbl_path = os.path.join(DATA_FOLDER, LBL_FILENAME)
img_path = os.path.join(DATA_FOLDER, IMG_FILENAME)
ensure_file_exists(lbl_path)
ensure_file_exists(img_path)

# -----------------------
# 1. Convert PDS (label) -> GeoTIFF (if not exists)
# -----------------------
out_topo_tif_path = os.path.join(DATA_FOLDER, OUT_TOPO_TIF)
if os.path.exists(out_topo_tif_path):
    print("✅ Topography GeoTIFF already exists:", out_topo_tif_path)
else:
    print("🔄 Converting PDS topography to GeoTIFF...")
    # Try multiple ways to open the PDS/IMG because some GDAL builds may not register the PDS driver
    ds = None
    candidates = [
        f"PDS:{lbl_path}",
        f"PDS:{img_path}",
        lbl_path,
        img_path,
        lbl_path.replace('\\', '/'),
        img_path.replace('\\', '/'),
    ]
    for candidate in candidates:
        try:
            ds = gdal.Open(candidate)
        except Exception:
            ds = None
        if ds is not None:
            print("Opened with GDAL:", candidate)
            break

    # Print whether the PDS driver is available (helps debugging)
    try:
        driver_count = gdal.GetDriverCount()
        has_pds = any(gdal.GetDriver(i).ShortName == 'PDS' for i in range(driver_count))
    except Exception:
        has_pds = False
    print("GDAL PDS driver available:", has_pds)

    if ds is None:
        raise RuntimeError(f"GDAL could not open PDS label or image: {lbl_path} / {img_path}\nTried candidates: {candidates}\nIf the PDS driver is missing in your GDAL build, consider installing a GDAL package that includes the PDS driver or use rasterio to read the raw .img directly.")
    # Translate to GeoTIFF
    gdal.Translate(out_topo_tif_path, ds, format="GTiff")
    ds = None
    print("💾 Converted to:", out_topo_tif_path)

# -----------------------
# 2. Load GeoTIFF with rasterio (CROP TO JEZERO CRATER)
# -----------------------
print("📥 Loading topography GeoTIFF with rasterio...")

# Jezero Crater bounding box in METERS (east longitudes)

# jezero_left   = 4580787.111167222  # meters (≈ 74.5°E)
# jezero_right  = 4630877.603791111   # meters (≈ 80.0°E)
# jezero_bottom = 1068155.337734444    # meters (≈ 16.5°N)
# jezero_top    = 1115709.447046667   # meters (≈ 20.0°N)

jezero_left = -6086970
jezero_right = -6041410
jezero_bottom = 1068460
jezero_top = 1115460


with rasterio.open(out_topo_tif_path) as src:
    print("📍 Cropping to Jezero region (meters)...")
    print(src.bounds)
    # Create window using bounds directly
    window = from_bounds(
        left=jezero_left,
        bottom=jezero_bottom,
        right=jezero_right,
        top=jezero_top,
        transform=src.transform
    )

    topo = src.read(1, window=window).astype(np.float64)
    transform = src.window_transform(window)
    profile = src.profile.copy()
    nodata = src.nodata

# Update profile size
profile.update({
    "height": topo.shape[0],
    "width": topo.shape[1],
    "transform": transform
})

print(f"✅ Cropped size: {topo.shape[1]} × {topo.shape[0]} pixels")

# Check if cropped region is large enough for calculations
if topo.shape[0] < 2 or topo.shape[1] < 2:
    print(f"❌ Cropped region too small for calculations: shape={topo.shape}. Expand bounds.")
    exit(1)

# Replace nodata with NaN for computations
if nodata is not None:
    topo = np.where(topo == nodata, np.nan, topo)
else:
    topo = topo.astype(np.float64)
    topo[np.isneginf(topo) | np.isposinf(topo)] = np.nan

# -----------------------
# 3. Determine pixel size in meters
#    Prefer reading MAP_SCALE from .lbl (KM/pixel)
# -----------------------
pixel_size_m = read_label_map_scale_km(lbl_path)
print(f"ℹ️ Using pixel size = {pixel_size_m:.2f} m/pixel (from MAP_SCALE in label)")

# -----------------------
# 4. Compute S1: Simple slope (degrees)
#    Using central differences via numpy.gradient which handles NaN by producing NaN
# -----------------------
print("🔢 Computing slope (degrees)...")
# Calculate pixel spacing in degrees
pixel_deg = 1 / 128.0  # 128 pixels per degree
# Mars mean radius in meters
mars_radius = 3396000.0
# Center latitude in degrees (Jezero Crater)
center_lat = 18.4
# Convert degree spacing to meters
lat_spacing_m = (np.pi / 180) * mars_radius * pixel_deg
lon_spacing_m = (np.pi / 180) * mars_radius * pixel_deg * np.cos(np.deg2rad(center_lat))
# Use these spacings in np.gradient
dz_dy, dz_dx = np.gradient(topo, lat_spacing_m, lon_spacing_m)
slope_rad = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
slope_deg = np.degrees(slope_rad)

# mask slope where topo is nan
slope_deg = np.where(np.isnan(topo), np.nan, slope_deg)

# -----------------------
# 6. Prepare profile and save outputs as GeoTIFFs
# -----------------------
print("💾 Saving outputs as GeoTIFFs...")

out_profile = profile.copy()
# force float32
out_profile.update(dtype=rasterio.float32, count=1, compress='lzw')

def save_tif(path, array, profile):
    arr = array.astype(np.float32)
    # ensure nodata is set (use NaN in file-friendly form)
    if np.isnan(arr).all():
        print("⚠️ All values are NaN for", path)
    # write
    with rasterio.open(path, 'w', **profile) as dst:
        dst.write(arr, 1)
    print("Saved:", path)

save_tif(os.path.join(DATA_FOLDER, OUT_TOPO_TIF), topo, out_profile)  # overwrite / confirm topo
save_tif(os.path.join(DATA_FOLDER, OUT_SLOPE_TIF), slope_deg, out_profile)

# -----------------------
# 7. Export slope grid to CSV
# -----------------------

n_bins_x = 100
n_bins_y = 100
height, width = slope_deg.shape
bin_height = height // n_bins_y
bin_width = width // n_bins_x

rows = []
for i in range(n_bins_y):
    for j in range(n_bins_x):
        y_start = i * bin_height
        y_end = (i + 1) * bin_height if i < n_bins_y - 1 else height
        x_start = j * bin_width
        x_end = (j + 1) * bin_width if j < n_bins_x - 1 else width
        bin_slope = slope_deg[y_start:y_end, x_start:x_end]
        avg_slope = np.nanmean(bin_slope)
        rows.append([j, i, avg_slope])

csv_path = os.path.join(DATA_FOLDER, "jezero_slope_grid.csv")
with open(csv_path, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["x", "y", "avg_slope"])
    writer.writerows(rows)
print(f"✅ Exported slope grid to {csv_path}")

# -----------------------
# 8. Quick plotting
# -----------------------
print("📊 Plotting quick figures...")
vmin_slope, vmax_slope = 0, np.nanpercentile(slope_deg, 98)

plt.figure(figsize=(8,6))
plt.imshow(slope_deg, vmin=vmin_slope, vmax=vmax_slope)
plt.title("Slope (deg)")
plt.colorbar(shrink=0.7)
plt.tight_layout()
plt.show()

print("✅ Done. Outputs saved in:", DATA_FOLDER)
