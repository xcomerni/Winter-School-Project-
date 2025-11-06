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

# -----------------------
# USER CONFIG
# -----------------------
DATA_FOLDER = r"C:\Users\zuzia\Documents\GitHub\Winter-School-Project-\MOLA"
# Label file for the topography product (you confirmed this exists)
LBL_FILENAME = "megt90n000eb.lbl"
IMG_FILENAME = "megt90n000eb.img"

# Output names (will be written into DATA_FOLDER)
OUT_TOPO_TIF = "mola_topography.tif"
OUT_SLOPE_TIF = "mola_slope_deg.tif"
OUT_ROUGH_STD_TIF = "mola_roughness_std.tif"
OUT_ROUGH_TRI_TIF = "mola_roughness_tri.tif"

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
jezero_left, jezero_right = 4000000, 5000000
jezero_bottom, jezero_top = 1000000, 1200000

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
# np.gradient expects spacing for each axis (first axis is rows -> y spacing)
# We assume square pixels: pixel_size_m for both axis
# gradient returns [d/dy, d/dx]
dz_dy, dz_dx = np.gradient(topo, pixel_size_m, pixel_size_m)
slope_rad = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
slope_deg = np.degrees(slope_rad)

# mask slope where topo is nan
slope_deg = np.where(np.isnan(topo), np.nan, slope_deg)

# -----------------------
# 5. Compute R3: roughness_std (3x3) and roughness_tri (TRI)
# -----------------------
print("🔢 Computing roughness products...")

def nanstd_window(values):
    # generic_filter passes flattened window; compute std ignoring NaNs
    arr_ = np.array(values)
    arr_ = arr_.astype(np.float64)
    arr_ = arr_[~np.isnan(arr_)]
    if arr_.size == 0:
        return np.nan
    return float(np.std(arr_, ddof=0))

# roughness_std: standard deviation in 3x3 window
roughness_std = generic_filter(topo, nanstd_window, size=3, mode='constant', cval=np.nan)

# roughness_tri: sum of absolute differences to 8 neighbours
def tri_window(values):
    # values is flattened 3x3 window with centre at index 4
    arr = np.array(values).reshape(3,3)
    center = arr[1,1]
    if np.isnan(center):
        return np.nan
    neigh = arr.flatten()
    # remove center
    neigh = np.delete(neigh, 4)
    # ignore nans in neighbors
    neigh = neigh[~np.isnan(neigh)]
    if neigh.size == 0:
        return np.nan
    return float(np.sum(np.abs(neigh - center)))

roughness_tri = generic_filter(topo, tri_window, size=3, mode='constant', cval=np.nan)

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
save_tif(os.path.join(DATA_FOLDER, OUT_ROUGH_STD_TIF), roughness_std, out_profile)
save_tif(os.path.join(DATA_FOLDER, OUT_ROUGH_TRI_TIF), roughness_tri, out_profile)

# -----------------------
# 7. Quick plotting
# -----------------------
print("📊 Plotting quick figures...")
vmin_slope, vmax_slope = 0, np.nanpercentile(slope_deg, 98)
vmin_rstd, vmax_rstd = 0, np.nanpercentile(roughness_std, 98)
vmin_rtri, vmax_rtri = 0, np.nanpercentile(roughness_tri, 98)

fig, axs = plt.subplots(1, 3, figsize=(18,6))
im0 = axs[0].imshow(slope_deg, vmin=vmin_slope, vmax=vmax_slope)
axs[0].set_title("Slope (deg)")
plt.colorbar(im0, ax=axs[0], shrink=0.7)

im1 = axs[1].imshow(roughness_std, vmin=vmin_rstd, vmax=vmax_rstd)
axs[1].set_title("Roughness (std dev, m)")
plt.colorbar(im1, ax=axs[1], shrink=0.7)

im2 = axs[2].imshow(roughness_tri, vmin=vmin_rtri, vmax=vmax_rtri)
axs[2].set_title("Roughness (TRI, m sum)")
plt.colorbar(im2, ax=axs[2], shrink=0.7)

plt.tight_layout()
plt.show()

print("✅ Done. Outputs saved in:", DATA_FOLDER)
