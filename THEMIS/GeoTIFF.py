# It builds a local solar time (LST) index from THEMIS PDS4 XML labels, then creates georeferenced brightness-temperature mosaics for multiple time “bands” over a Jezero crater bounding box.
# It reprojects each input (using label bounds if needed), computes a per-pixel median and coverage count, and saves GeoTIFFs; it also reports global temperature ranges for consistent visualization.


import sys
# Note: the following line works in Colab/Jupyter; if you run it as a plain .py, comment it out.
!{sys.executable} -m pip install rasterio
import numpy, rasterio
print("NumPy:", numpy.__version__)
print("Rasterio:", rasterio.__version__)

# --- MOUNT (if using Colab) ---
try:
    from google.colab import drive
    drive.mount('/content/drive')
except Exception:
    pass

# PUT HERE the folder where the XML files are located (for the initial LST index).
# Examples:
#   path = "/content"                       # direct upload in Colab
#   path = "/content/drive/MyDrive/THEMIS"  # on Drive
path = "/content/drive/MyDrive/winter_school/INTERSTELLAR_ALLIANCE/THEMIS/michelle version/data/all_data"

# ====================== LST INDEX (as in your script) ======================
import glob, os, re, xml.etree.ElementTree as ET
import pandas as pd

xml_paths = sorted(glob.glob(os.path.join(path, "*.xml")))
print(f"Trovati {len(xml_paths)} file XML")
for p in xml_paths[:10]:
    print(" -", os.path.basename(p))

def extract_text_any(elem):
    if elem is None:
        return None
    txt = (elem.text or "").strip()
    return txt or None

def find_first_by_tag_name_anyns(root, wanted_names):
    wanted = {w.lower() for w in wanted_names}
    for elem in root.iter():
        tag = elem.tag.split('}', 1)[-1].lower()
        if tag in wanted:
            return elem
    return None

def extract_lst_from_label(xml_file):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except Exception:
        return None

    candidate_tags = [
        "local_true_solar_time",
        "start_local_true_solar_time",
        "stop_local_true_solar_time",
        "local_solar_time",
    ]
    node = find_first_by_tag_name_anyns(root, candidate_tags)
    txt = extract_text_any(node)

    if not txt:
        try:
            with open(xml_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except:
            content = ""
        m = re.search(r"\b(\d{1,2}:\d{2}:\d{2}(?:\.\d+)?)\b", content)
        txt = m.group(1) if m else None

    if not txt:
        return None

    m = re.match(r"^\s*(\d{1,2}):(\d{2}):(\d{2}(?:\.\d+)?)\s*$", txt)
    if not m:
        return txt.strip()
    hh = int(m.group(1)); mm = m.group(2); ss = m.group(3)
    return f"{hh:02d}:{mm}:{ss}"

rows = []
for p in xml_paths:
    file_id = os.path.splitext(os.path.basename(p))[0]
    lst = extract_lst_from_label(p)
    rows.append({"file_id": file_id, "LST": lst})

df = pd.DataFrame(rows).sort_values(["LST", "file_id"], na_position="last").reset_index(drop=True)
print(df.head(10))
out_csv = "/content/themis_lst_index.csv"
try:
    df.to_csv(out_csv, index=False)
    print("CSV salvato in:", out_csv)
except Exception as e:
    print("Non posso salvare CSV:", e)

# ====================== BT MOSAICS — 4 BANDS ======================
import os, glob, math, xml.etree.ElementTree as ET
import numpy as np
import rasterio
from rasterio.warp import reproject
from rasterio.enums import Resampling
from rasterio.transform import from_bounds, Affine
from rasterio.crs import CRS
import matplotlib.pyplot as plt

# -------- CONFIG: specify your XMLs for each band --------
# Glob patterns are also accepted. You can use .xml or .img (the script tries to find the matching .xml).

# band 1: 5:30
# band 2: 7:00
# band 3: 19:00
# band 4: 18:30

FASCIA_1_XMLS = [
    "/content/drive/MyDrive/winter_school/INTERSTELLAR_ALLIANCE/THEMIS/michelle version/data/all_data/I92413021BTR.xml",
    "/content/drive/MyDrive/winter_school/INTERSTELLAR_ALLIANCE/THEMIS/michelle version/data/all_data/I92987012BTR.xml",
]
FASCIA_2_XMLS = [
     "/content/drive/MyDrive/winter_school/INTERSTELLAR_ALLIANCE/THEMIS/michelle version/data/all_data/I97392006BTR.xml",
     "/content/drive/MyDrive/winter_school/INTERSTELLAR_ALLIANCE/THEMIS/michelle version/data/all_data/I97679002BTR.xml",
]
FASCIA_3_XMLS = [
    "/content/drive/MyDrive/winter_school/INTERSTELLAR_ALLIANCE/THEMIS/michelle version/data/all_data/I97348005BTR.xml",
    "/content/drive/MyDrive/winter_school/INTERSTELLAR_ALLIANCE/THEMIS/michelle version/data/all_data/I98521009BTR.xml",
]
FASCIA_4_XMLS = [
    "/content/drive/MyDrive/winter_school/INTERSTELLAR_ALLIANCE/THEMIS/michelle version/data/all_data/I99694010BTR.xml",
    "/content/drive/MyDrive/winter_school/INTERSTELLAR_ALLIANCE/THEMIS/michelle version/data/all_data/I99120007BTR.xml",
                 ]

# Jezero BBOX in degrees (E+, N+)
BBOX_DEG   = [77.2663, 18.0077, 78.1112, 18.8094]     # [minlon, minlat, maxlon, maxlat]
TARGET_RES_M = 150.0                      # e.g. 100–200 m/px; increase if you need less RAM
MAX_PIXELS   = 60_000_000                 # safe RAM budget
# ------------------------------------------------

MARS_R = 3396190.0
MARS_GEOG = CRS.from_string("+proj=longlat +a=3396190 +b=3396190 +no_defs +type=crs")

def eqc_crs(lon0):
    return CRS.from_string(f" +proj=eqc +lat_ts=0 +lat_0=0 +lon_0={lon0} +a={MARS_R} +b={MARS_R} +units=m +no_defs")

def _paths(lst):
    out=[]
    for p in lst:
        out += sorted(glob.glob(p)) if any(ch in p for ch in "*?[]") else [p]
    fixed=[]
    for p in out:
        if p.lower().endswith(".xml"):
            fixed.append(p)
        elif p.lower().endswith(".img"):
            x = os.path.splitext(p)[0] + ".xml"
            fixed.append(x if os.path.exists(x) else p)
        else:
            fixed.append(p)
    return [p for p in fixed if os.path.exists(p)]

def _looks_identity(t: Affine) -> bool:
    return (abs(t.a-1)<1e-9 and abs(t.b)<1e-9 and abs(t.c)<1e-9 and
            abs(t.d)<1e-9 and abs(t.e-1)<1e-9 and abs(t.f)<1e-9)

def parse_pds4_bounds(xml_path):
    """Restituisce (west, east, south, north) in °. Supporta tag min/max/westernmost/easternmost."""
    try:
        root = ET.parse(xml_path).getroot()
        def find_first(names):
            for el in root.iter():
                tag = el.tag.split('}')[-1].lower()
                if tag in names and el.text:
                    try: return float(el.text)
                    except: pass
            return None
        west  = find_first({"minimum_longitude","westernmost_longitude","west_bounding_coordinate",
                            "minimumlongitude","westernmostlongitude"})
        east  = find_first({"maximum_longitude","easternmost_longitude","east_bounding_coordinate",
                            "maximumlongitude","easternmostlongitude"})
        south = find_first({"minimum_latitude","south_bounding_coordinate","minimumlatitude"})
        north = find_first({"maximum_latitude","north_bounding_coordinate","maximumlatitude"})
        if None in (west, east, south, north): return None
        if west < 0 and east < 0:  # normalize if both negative
            west += 360.0; east += 360.0
        return west, east, south, north
    except Exception as e:
        print(f"[warn] parse_pds4_bounds: {os.path.basename(xml_path)} -> {e}")
        return None

def make_grid(bbox, res_m):
    minlon, minlat, maxlon, maxlat = map(float, bbox)
    lon0 = 0.5*(minlon+maxlon)
    crs  = eqc_crs(lon0)
    left   =  MARS_R * math.radians(minlon - lon0)
    right  =  MARS_R * math.radians(maxlon - lon0)
    bottom =  MARS_R * math.radians(minlat)
    top    =  MARS_R * math.radians(maxlat)
    W = max(1, int(math.ceil((right-left)/res_m)))
    H = max(1, int(math.ceil((top-bottom)/res_m)))
    if W*H > MAX_PIXELS:
        scale = math.sqrt((W*H)/MAX_PIXELS)
        res_m *= scale
        W = int(math.ceil((right-left)/res_m)); H = int(math.ceil((top-bottom)/res_m))
        print(f"[info] res adattata: ~{res_m:.1f} m/px (grid {W}x{H})")
    transform = from_bounds(left, bottom, right, top, W, H)
    return crs, transform, W, H, lon0, res_m

def repro_stack(paths, dst_crs, dst_transform, W, H):
    stack=[]
    for p in paths:
        with rasterio.open(p) as src:
            arr = src.read(1).astype("float32")

            # Apply scale/offset if present
            try:
                s = float((getattr(src, "scales",  [1.0]) or [1.0])[0])
                o = float((getattr(src, "offsets", [0.0]) or [0.0])[0])
                if s != 1.0 or o != 0.0:
                    arr = arr * s + o
            except Exception:
                pass

            nod = src.nodata if src.nodata is not None else 0.0  # many BTR use 0 K as nodata
            src_crs = src.crs
            src_tf  = src.transform

            # Fallback georef from .xml
            if (src_crs is None) or _looks_identity(src_tf):
                bounds = parse_pds4_bounds(p)
                if bounds is None:
                    raise RuntimeError(f"{os.path.basename(p)}: manca georeferenza e non trovo i bounds nel .xml")
                Wdeg, Edeg, Sdeg, Ndeg = bounds
                src_crs = MARS_GEOG
                src_tf  = from_bounds(Wdeg, Sdeg, Edeg, Ndeg, src.width, src.height)
                print(f"[ok] {os.path.basename(p)}: georef da label (lon/lat) -> ({Wdeg:.3f},{Sdeg:.3f})–({Edeg:.3f},{Ndeg:.3f})")

            dst = np.full((H,W), np.nan, dtype="float32")
            reproject(
                source=arr, destination=dst,
                src_transform=src_tf, src_crs=src_crs, src_nodata=nod,
                dst_transform=dst_transform, dst_crs=dst_crs, dst_nodata=np.nan,
                resampling=Resampling.bilinear
            )
            stack.append(dst)
            print(f"[ok] reproiettato {os.path.basename(p)}  | nodata={nod}")
    return np.stack(stack, axis=0) if stack else np.empty((0,H,W), dtype="float32")

def mosaic_median_count(paths, dst_crs, dst_transform, W, H, label):
    if not paths: return None, None
    S = repro_stack(paths, dst_crs, dst_transform, W, H)
    if S.shape[0]==0: return None, None
    valid = np.isfinite(S)
    count = valid.sum(axis=0).astype("float32")
    with np.errstate(all="ignore"):
        med = np.nanmedian(S, axis=0).astype("float32")  # same robust choice as your script
    med[count==0] = np.nan
    print(f"[{label}] scene={S.shape[0]}, coverage={(count>0).mean()*100:.1f}%")
    return med, count

def save_tif(path, arr, transform, crs, nodata=np.nan):
    prof={"driver":"GTiff","height":arr.shape[0],"width":arr.shape[1],
          "count":1,"dtype":"float32","crs":crs,"transform":transform,
          "compress":"DEFLATE","tiled":True,"nodata":nodata}
    with rasterio.open(path,"w",**prof) as dst: dst.write(arr,1)
    print("TIF:", path)

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
    lonL = lon0 + math.degrees(x0/MARS_R); lonR = lon0 + math.degrees(x1/MARS_R)
    latB = math.degrees(y1/MARS_R);       latT = math.degrees(y0/MARS_R)
    
    plt.figure(figsize=(8,6), dpi=140)
    # Pass vmin and vmax directly to imshow for consistent scaling
    im = plt.imshow(arr, cmap=cmap, origin="upper", extent=[lonL,lonR,latB,latT], vmin=lo, vmax=hi)
    plt.xlabel("Longitude (°E)"); plt.ylabel("Latitude (°N)")
    plt.title(title); plt.grid(alpha=0.3); plt.tight_layout()
    plt.colorbar(im, label=cbar_label) # Add colorbar with label
    plt.savefig(out_png, dpi=200); plt.close()
    print("PNG:", out_png)

# ---- RUN ----
FASCIA_1_XMLS = _paths(FASCIA_1_XMLS)
FASCIA_2_XMLS = _paths(FASCIA_2_XMLS)
FASCIA_3_XMLS = _paths(FASCIA_3_XMLS)
FASCIA_4_XMLS = _paths(FASCIA_4_XMLS)

tutte = FASCIA_1_XMLS + FASCIA_2_XMLS + FASCIA_3_XMLS + FASCIA_4_XMLS
if not tutte:
    raise SystemExit("Inserisci 2–3 XML per almeno una fascia (FASCIA_1_XMLS / FASCIA_2_XMLS / FASCIA_3_XMLS / FASCIA_4_XMLS).")

print(f"res target ~{TARGET_RES_M:.1f} m/px")
dst_crs, dst_tf, W, H, lon0, TARGET_RES_M = make_grid(BBOX_DEG, TARGET_RES_M)
print(f"griglia {W}x{H} | CRS eqc lon0≈{0.5*(BBOX_DEG[0]+BBOX_DEG[2]):.3f}")

# (Audit) print bounds read by the parser
for fp in tutte:
    print(os.path.basename(fp), "bounds:", parse_pds4_bounds(fp))

# define fasce as a dictionary: {name: file_list}
fasce = {
    "fascia_1": FASCIA_1_XMLS,
    "fascia_2": FASCIA_2_XMLS,
    "fascia_3": FASCIA_3_XMLS,
    "fascia_4": FASCIA_4_XMLS,
}

# Dictionary to store processed BT and Count arrays for each band
fasce_data = {}
all_bt_values_for_global_scale = []

# Define the LST times for each band
fascia_times = {
    "fascia_1": "5:30 AM",
    "fascia_2": "7:00 AM",
    "fascia_3": "7:00 PM",
    "fascia_4": "6:30 PM",
}

for nome, lista in fasce.items():
    if not lista:
        print(f"[skip] {nome}: nessun file")
        continue
    bt, cnt = mosaic_median_count(lista, dst_crs, dst_tf, W, H, nome.upper())
    if bt is None:
        print(f"[warn] {nome}: stack vuoto")
        continue
    
    fasce_data[nome] = {"bt": bt, "cnt": cnt}
    
    # Collect all valid BT values for global min/max calculation
    mask = np.isfinite(bt)
    if mask.any():
        all_bt_values_for_global_scale.append(bt[mask])

# Calculate global min/max for consistent colorbar across all plots
global_lo, global_hi = None, None
if all_bt_values_for_global_scale:
    all_bt_values_flat = np.concatenate(all_bt_values_for_global_scale)
    global_lo = np.percentile(all_bt_values_flat, 2)
    global_hi = np.percentile(all_bt_values_flat, 98)
    print(f"[info] Global temperature range (2nd-98th percentile): {global_lo:.2f}K - {global_hi:.2f}K")

# Loop again to save TIFs
for nome, data in fasce_data.items():
    bt  = data["bt"]
    cnt = data["cnt"]

    # Get the time string and sanitize it for filename
    time_str = fascia_times.get(nome, "Unknown_Time").replace(" ", "").replace(":", "_")

    # Saves (same formats as your script)
    tif_bt   = f"/content/themis_BT_{time_str}_median.tif"
    tif_cnt  = f"/content/themis_BT_{time_str}_count.tif"
    save_tif(tif_bt,  bt,  dst_tf, dst_crs)
    save_tif(tif_cnt, cnt, dst_tf, dst_crs, nodata=0)

print("Elaborazione e salvataggio TIF completati.")

