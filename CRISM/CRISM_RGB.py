# Colab version

# -- 1) Drive --
import os
from google.colab import drive

# Attempt to unmount and remove the mount directory
try:
  drive.flush_and_unmount()
except ValueError:
  pass  # Ignore if not mounted

if os.path.exists('/content/drive'):
  !rm -rf /content/drive

drive.mount('/content/drive', force_remount=True)

# Install necessary libraries
!pip install rasterio==1.3.10 geopandas shapely pyproj matplotlib

# ============================================================
# CRISM • SR/SU MTRDR → per-scene in EQC + MOSAIC RGB
# - For each scene: extract D2300, BD2210, BD1900 → reproject EQC
#   with NoData=NaN and "footprint mask" → save 3-raw bands
# - Then: mosaic for each band (method='max', nodata=np.nan) → final RGB with alpha
# ============================================================


# 2) Import
import os, re, numpy as np, rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.io import MemoryFile
from rasterio.crs import CRS
from rasterio.merge import merge
import matplotlib.pyplot as plt
from pyproj import Transformer # Import Transformer for coordinate conversion

# Avoid check Earth/Mars if metadata is missing
os.environ["PROJ_IGNORE_CELESTIAL_BODY"] = "YES"


# 3) CONFIG — MODIFY HERE
# ===========================
SR_PATHS = [
    "/content/drive/MyDrive/winter_school/INTERSTELLAR_ALLIANCE/DATA/CRISM DATAS (3 ZONE)/frt000047a3_07_sr166j_mtr3.img",
   "/content/drive/MyDrive/winter_school/INTERSTELLAR_ALLIANCE/DATA/CRISM DATAS (3 ZONE)/frt00005850_07_sr167j_mtr3.img",
   "/content/drive/MyDrive/winter_school/INTERSTEALLAR_ALLIANCE/DATA/CRISM DATAS (3 ZONE)/frt00005c5e_07_sr166j_mtr3.img",
   "/content/drive/MyDrive/winter_school/INTERSTELLAR_ALLIANCE/DATA/CRISM DATAS (3 ZONE)/frt0001c558_07_sr165j_mtr3.img",
    "/content/drive/MyDrive/winter_school/INTERSTELLAR_ALLIANCE/DATA/CRISM DATAS (3 ZONE)/frt00021da6_07_sr166j_mtr3.img",
    "/content/drive/MyDrive/winter_school/INTERSTELLAR_ALLIANCE/DATA/CRISM DATAS (3 ZONE)/frt00021da6_07_sr166j_mtr3.img",
    "/content/drive/MyDrive/winter_school/INTERSTELLAR_ALLIANCE/DATA/CRISM DATAS (3 ZONE)/frt0001ecba_07_sr166j_mtr3.img",
    "/content/drive/MyDrive/winter_school/INTERSTELLAR_ALLIANCE/DATA/CRISM DATAS (3 ZONE)/frt0001fb74_07_sr166j_mtr3.img",
    "/content/drive/MyDrive/winter_school/INTERSTELLAR_ALLIANCE/DATA/CRISM DATAS (3 ZONE)/hrl000040ff_07_sr183j_mtr3.img",
    "/content/drive/MyDrive/winter_school/INTERSTELLAR_ALLIANCE/DATA/CRISM DATAS (3 ZONE)/hrl00010963_07_sr183j_mtr3.img",
    "/content/drive/MyDrive/winter_school/INTERSTELLAR_ALLIANCE/DATA/CRISM DATAS (3 ZONE)/hrl000116c6_07_sr183j_mtr3.img"

]

OUT_DIR = "/content/drive/MyDrive/CRISM/Jezero/mosaic_rgb"
os.makedirs(OUT_DIR, exist_ok=True)

# Projections (Mars)
MARS_EQC  = CRS.from_string("+proj=eqc +lat_ts=0 +lat_0=0 +lon_0=0 +a=3396190 +b=3396190 +units=m +no_defs")
MARS_GEOG = CRS.from_string("+proj=longlat +a=3396190 +b=3396190 +no_defs")  # fallback per SR senza CRS
TARGET_RES_M = 200  # m/px (100 o 72 per più dettaglio)

# Band aliases (as per single workflow)
BAND_ALIASES = {
  "BD1900": ["BD1900","BD1900_2","BD1900_1"],
  "D2300":  ["D2300"],
  "BD2210": ["BD2210","D2200","D2200_1","D2200_2"],
}

# ===========================
# 4) Utility

def find_idx(targets, names):
    N=[(n or "").upper() for n in names]
    for t in targets:
        tU=t.upper()
        for i,n in enumerate(N):
            if n==tU or tU in n: return i+1
    return None

def reproject_match(src_ds, dst_crs, dst_res):
    """Riproietta tutto lo stack a dst_crs, risoluzione dst_res, con NoData=NaN."""
    """Reprojects the entire stack to dst_crs, dst_res resolution, with NoData=NaN."""
    transform, width, height = calculate_default_transform(
        src_ds.crs, dst_crs, src_ds.width, src_ds.height, *src_ds.bounds, resolution=dst_res
    )
    profile = src_ds.profile.copy()
    profile.update({"crs": dst_crs, "transform": transform, "width": width, "height": height})
    data = np.full((src_ds.count, height, width), np.nan, dtype="float32")  # buffer a NaN
    for i in range(1, src_ds.count+1):
        reproject(
            source=rasterio.band(src_ds, i),
            destination=data[i-1],
            src_transform=src_ds.transform, src_crs=src_ds.crs,
            dst_transform=transform,   dst_crs=dst_crs,
            resampling=Resampling.bilinear,
            src_nodata=src_ds.nodata,
            dst_nodata=np.nan,  # <<< elimina dati nulli
        )
    return data, profile

def robust_norm(a):
    v=a[np.isfinite(a)]
    if v.size==0: return np.zeros_like(a, dtype=np.float32)
    vmin,vmax=np.percentile(v,[2,98])
    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmax<=vmin:
        return np.zeros_like(a, dtype=np.float32)
    out=(a-vmin)/(vmax-vmin)
    return np.clip(out,0,1).astype(np.float32)

def save_rgba(path, R, G, B, alpha_mask):
    A = np.where(alpha_mask, 1.0, 0.0).astype(np.float32)
    rgba = np.stack([R,G,B,A], axis=-1)
    plt.imsave(path, rgba)


# 5) Per-scene → Raw 3-band (EQC) with clean footprint
# ===========================
scene_tifs = []
skipped = []

for p in SR_PATHS:
    assert os.path.exists(p), f"Manca: {p}"
    ds0 = rasterio.open(p)

    # If CRS is missing, declare Martian geographic CRS for reprojection
    if ds0.crs is None:
        arr0 = ds0.read()
        prof0 = ds0.profile.copy(); prof0.update({"crs": MARS_GEOG})
        mem = MemoryFile()
        with mem.open(**prof0) as tmp:
            for i in range(arr0.shape[0]): tmp.write(arr0[i], i+1)
        ds = mem.open()
    else:
        ds = ds0

    names = list(ds.descriptions) if (ds.descriptions and ds.descriptions[0] is not None) else [f"B{i}" for i in range(1, ds.count+1)]
    i_b1900 = find_idx(BAND_ALIASES["BD1900"], names)
    i_d2300 = find_idx(BAND_ALIASES["D2300"],  names)
    i_b2210 = find_idx(BAND_ALIASES["BD2210"], names)
    if not (i_b1900 and i_d2300 and i_b2210):
        skipped.append(os.path.basename(p)); continue  # probably IF/TRDR or SR without indices

    # Reproject the entire stack as in the single code, but with NoData=NaN
    arr_rp, prof_rp = reproject_match(ds, MARS_EQC, TARGET_RES_M)

    # Footprint mask: keep only the actual swath footprint
    D23   = arr_rp[i_d2300-1]
    BD221 = arr_rp[i_b2210-1]
    BD190 = arr_rp[i_b1900-1]
    stack = np.stack([D23, BD221, BD190], axis=0)
    foot  = np.isfinite(stack).any(axis=0)                          # at least one valid band
    foot &= (np.nan_to_num(stack, nan=0.0).sum(axis=0) > 0.0)       # avoid filling zeros
    
    # optional: remove residual near-zero values
    tiny = (np.nan_to_num(stack, nan=0.0).max(axis=0) < 1e-7)
    foot &= ~tiny

    D23[~foot]   = np.nan
    BD221[~foot] = np.nan
    BD190[~foot] = np.nan

    # Save the raw 3-band (ordered for RGB: 1=D2300, 2=BD2210, 3=BD1900)
    prof_out = prof_rp.copy()
    prof_out.update({"count": 3, "dtype": "float32", "driver": "GTiff",
                     "nodata": np.nan, "compress": "LZW", "tiled": True})
    scene_id = re.sub(r"\.img$", "", os.path.basename(p))
    out_tif = os.path.join(OUT_DIR, f"{scene_id}_indices_eqc.tif")
    with rasterio.open(out_tif, "w", **prof_out) as dst:
        dst.write(D23.astype("float32"),   1); dst.set_band_description(1, "D2300")
        dst.write(BD221.astype("float32"), 2); dst.set_band_description(2, "BD2210")
        dst.write(BD190.astype("float32"), 3); dst.set_band_description(3, "BD1900")
    scene_tifs.append(out_tif)

    # Per-scene Quicklook (optional but useful)
    R,G,B = robust_norm(D23), robust_norm(BD221), robust_norm(BD190)
    save_rgba(os.path.join(OUT_DIR, f"{scene_id}_RGB.png"), R,G,B, np.isfinite(D23)&np.isfinite(BD221)&np.isfinite(BD190))


print(f"Scene valide: {len(scene_tifs)}")
if skipped:
    print("⚠️ Saltate (non Summary/indici mancanti):", skipped)
# Skipped (not Summary/missing indices)
if len(scene_tifs)==0:
    raise SystemExit("Nessuna scena valida: usa file *_sr*_mtr3.img (o *_su*_mtr3.img).")
# No valid scenes: use *_sr*_mtr3.img (or *_su*_mtr3.img) files.


# 6) Mosaic per band (respects NoData) + RGB with alpha
# ===========================
srcs = [rasterio.open(t) for t in scene_tifs]
# merge multi-band, method 'max', and especially nodata=np.nan
mosaic, trans = merge(srcs, method='max', nodata=np.nan)
# Bands: [0]=D2300, [1]=BD2210, [2]=BD1900
D23_m, BD221_m, BD190_m = mosaic[0], mosaic[1], mosaic[2]
valid = np.isfinite(D23_m) | np.isfinite(BD221_m) | np.isfinite(BD190_m) # Use OR to check for any valid band

# RGB with global normalization and alpha outside the footprint
R,G,B = robust_norm(D23_m), robust_norm(BD221_m), robust_norm(BD190_m)
rgba_path = os.path.join(OUT_DIR, "jezero_CRISM_RGB_mosaic.png")
# The alpha mask should be based on whether *any* band has valid data for that pixel
save_rgba(rgba_path, R,G,B, valid)


# Also save the raw 3-band GeoTIFF of the mosaic
prof_m = srcs[0].profile.copy()
prof_m.update({"height": mosaic.shape[1], "width": mosaic.shape[2],
               "transform": trans, "count": 3, "dtype": "float32",
               "driver": "GTiff", "nodata": np.nan, "compress": "LZW", "tiled": True})
tif_mosaic = os.path.join(OUT_DIR, "jezero_CRISM_indices_mosaic.tif")
with rasterio.open(tif_mosaic, "w", **prof_m) as dst:
    dst.write(D23_m.astype("float32"),   1); dst.set_band_description(1, "D2300")
    dst.write(BD221_m.astype("float32"), 2); dst.set_band_description(2, "BD2210")
    dst.write(BD190_m.astype("float32"), 3); dst.set_band_description(3, "BD1900")

for s in srcs: s.close()

print("✅ PNG RGB con alpha:", rgba_path)
print("✅ GeoTIFF 3-bande (grezzo):", tif_mosaic)

# Add code to display the saved image with Lat/Lon axes
if os.path.exists(rgba_path):
    img = plt.imread(rgba_path)
    fig, ax = plt.subplots(figsize=(10, 10)) # Create figure and axes explicitly

    # Set the background color inside the plot to white
    ax.set_facecolor('white')

    # Display the image
    # Use extent to position the image correctly based on spatial coordinates
    # Need the transform ('trans') from the merge step
    extent = [trans[2], trans[2] + img.shape[1] * trans[0],
              trans[5] + img.shape[0] * trans[4], trans[5]] # Calculate extent from transform
    im = ax.imshow(img, extent=extent)

    plt.title("Jezero CRISM SR RGB Mosaic (D2300, BD2210, BD1900)")

    # Add legend text outside the plot
    legend_text = """
R = D2300 (Fe/Mg)
G = BD2210 (Al-OH)
B = BD1900 (H2O)
    """
    # Position the legend text outside the plot area and adjust horizontal alignment
    plt.text(
        1.02, # X-coordinate relative to the axes (1.0 is the right edge)
        1.0,  # Y-coordinate relative to the axes (1.0 is the top edge)
        legend_text.strip(),
        color='black', # Changed color to black for better visibility outside the plot
        fontsize=10,
        ha='left', # Align text to the left
        va='top',  # Align text to the top
        transform=ax.transAxes, # Use axes coordinates for positioning
        bbox=dict(facecolor='white', alpha=0.8, edgecolor='black') # Add a background box
    )

    # --- Add code for Lat/Lon axes and cropping ---
    try:
        # Transformer from Geographic (degrees) to EQC (meters)
        transformer = Transformer.from_crs("EPSG:4326", MARS_EQC, always_xy=True)

        # Transform the user-provided Lat/Lon coordinates to EQC
        crop_lon_min = 77.2663 # Western most longitude in degrees
        crop_lat_min = 18.0077 # Minimum latitude in degrees
        crop_lon_max = 78.1112 # Eastern most longitude in degrees
        crop_lat_max = 18.8094 # Maximum latitude in degrees


        # Note: transformer.transform returns (lon, lat) for EPSG:4326 when always_xy=True
        # Need to ensure correct order for EQC (x, y) which corresponds to (lon, lat) in this projection
        crop_xmin, crop_ymin = transformer.transform(crop_lon_min, crop_lat_min)
        crop_xmax, crop_ymax = transformer.transform(crop_lon_max, crop_lat_max)

        print(f"Crop EQC limits: xmin={crop_xmin}, xmax={crop_xmax}, ymin={crop_ymin}, ymax={crop_ymax}")
        print(f"Image EQC extent: {extent}")

        # Set the x and y limits of the plot using the transformed EQC coordinates
        # Need to handle the potential reversal of y-axis depending on the image orientation
        # Assuming standard image orientation where y increases downwards, the extent y-coordinates are [ymax, ymin]
        # So for cropping, the plot limits should be set with the transformed ymin and ymax
        ax.set_xlim(crop_xmin, crop_xmax)
        ax.set_ylim(crop_ymin, crop_ymax) # Use transformed ymin and ymax directly

        # Define tick locations in EQC coordinates (e.g., 5 ticks) based on the cropped extent
        current_xlim = ax.get_xlim()
        current_ylim = ax.get_ylim()

        xticks_eqc = np.linspace(current_xlim[0], current_xlim[1], 5)
        yticks_eqc = np.linspace(current_ylim[1], current_ylim[0], 5) # Note reversal for y-axis limits

        # Transform EQC coordinates of ticks to geographic (Lat/Lon) for labels
        transformer_inv = Transformer.from_crs(MARS_EQC, "EPSG:4326", always_xy=True)
        xticks_lon_arr, _ = transformer_inv.transform(xticks_eqc, [current_ylim[0]]*len(xticks_eqc)) # Use the south extent for Y
        _, yticks_lat_arr = transformer_inv.transform([current_xlim[0]]*len(yticks_eqc), yticks_eqc) # Use the west extent for X

        print(f"Y-axis EQC tick locations (after cropping): {yticks_eqc}")
        print(f"Transformed Y-axis Latitude labels (after cropping): {yticks_lat_arr}")

        # Set the tick positions and labels using EQC coordinates from the cropped extent
        ax.set_xticks(xticks_eqc)
        ax.set_xticklabels([f'{lon:.2f}°E' for lon in xticks_lon_arr]) # Iterate over the array
        ax.set_xlabel("Longitude")

        # Y-axis needs to be set with EQC coordinates but labeled with transformed geographic
        ax.set_yticks(yticks_eqc)
        # Reverse the order of yticks_lat to match the image's y-axis direction (south to north)
        ax.set_yticklabels([f'{lat:.2f}°N' for lat in yticks_lat_arr]) # Iterate over the array

        ax.set_ylabel("Latitude")


        # Ensure tight layout to remove excessive white space
        plt.tight_layout(rect=[0, 0, 0.8, 1]) # Adjust rect to make space for the legend

    except NameError:
        print("Could not find 'trans' or 'MARS_EQC'. Please run the mosaic generation cell first.")
    except Exception as e:
        print(f"An error occurred while trying to set Lat/Lon axes or crop: {e}")

    # --- End code for Lat/Lon axes and cropping ---

    # plt.show() # Do not show the plot here, pass fig and ax to the next cell
    pass # Do not show the plot here

# Return fig and ax so the next cell can use them
fig, ax
