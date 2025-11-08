# CRISM — RGB, Mesh, Data & Percentages (5-step pipeline)

This README documents the `CRISM` folder and the **execution order** of the codes.  
The pipeline produces RGB visualizations, a 3D-styled mesh view with axes, and per-cell statistics/percentages for three CRISM indices.

---

## Execution order (run in this order)

1. `CRISM_RGB`
2. `CRISM_mesh`
3. `CRISM_mesh_axis`
4. `CRISM_data`
5. `CRISM_data_percentage`

Each step consumes the outputs produced by the previous step.

---

## What each step does (as implemented in the current codebase)

### 1) `CRISM_RGB`
**Purpose:** Build RGB images from CRISM **MTRDR SR/SU** products and (optionally) save per-scene 3-band GeoTIFFs.

- **Inputs**
  - Multiple CRISM MTRDR `*_sr*_mtr3.img` (or `*_su*_mtr3.img`) files.
  - Edit paths in a configuration section (list of `SR_PATHS`) before running.

- **Mineral-to-RGB mapping (exact)**
  - **R = D2300** (Fe/Mg smectites)
  - **G = BD2210** (Al-OH clays; aliases include `BD2210`, `D2200`, `D2200_1`, `D2200_2`)
  - **B = BD1900** (H₂O / hydrated phases; aliases `BD1900`, `BD1900_2`, `BD1900_1`)

- **Processing details**
  - If input CRS is missing, assign **Mars geographic** (`+proj=longlat +a=3396190 +b=3396190`) to allow reprojection.
  - Reproject to **Mars EQC** (`+proj=eqc ... +a=3396190 +b=3396190`) at `TARGET_RES_M` (default **200 m/px**).
  - Clean footprint using “any-band-valid AND sum>0” logic; remove tiny residuals.
  - Save per-scene:
    - **RGB quicklook** (`<scene>_RGB.png`) using **robust 2–98% normalization** per channel.
    - **3-band GeoTIFF** (`<scene>_indices_eqc.tif`, float32; band 1=D2300, 2=BD2210, 3=BD1900).

> Env hint: `PROJ_IGNORE_CELESTIAL_BODY=YES` is set to bypass Earth/Mars checks when metadata is incomplete.

---

### 2) `CRISM_mesh`
**Purpose:** Build a **mosaic** from the per-scene 3-band products and generate a mesh-like view (surface/heatmap) of the RGB composite.

- **Inputs**
  - The per-scene `*_indices_eqc.tif` files from step 1.

- **Processing details**
  - Mosaic with `rasterio.merge.merge(..., method='max', nodata=np.nan)`.
  - Save:
    - **3-band mosaic GeoTIFF**: `jezero_CRISM_indices_mosaic.tif` (bands = D2300, BD2210, BD1900).
    - **RGBA PNG**: `jezero_CRISM_RGB_mosaic.png` with **alpha where no band is valid**.

---

### 3) `CRISM_mesh_axis`
**Purpose:** Add **geographic axes** and a **user crop** to the mosaic view; prepare a regular **100×100 grid** overlay.

- **Inputs**
  - `jezero_CRISM_RGB_mosaic.png` and transform/CRS from `jezero_CRISM_indices_mosaic.tif`.

- **Processing details**
  - Convert a lon/lat crop box (deg) to EQC and apply limits.
  - Draw lat/lon tick labels (°E/°N) using inverse transform.
  - Overlay a **100×100** regular grid across the cropped extent.
  - Save the meshed view: `jezero_CRISM_RGB_mosaic_meshed.png`.

---

### 4) `CRISM_data`
**Purpose:** Compute **per-cell averages** for the three indices over the 100×100 grid (on the cropped mosaic).

- **Inputs**
  - `jezero_CRISM_indices_mosaic.tif` and the crop extent from step 3.

- **Processing details**
  - For each grid cell, convert EQC bounds → raster window and extract:
    - `Avg_D2300`, `Avg_BD2210`, `Avg_BD1900` (NaN-aware means).
  - Replace NaNs with 0 **only at CSV write time** (to keep a dense table).
  - Save: **`mesh_mineral_averages.csv`** with columns:
    ```
    x, y, Avg_D2300, Avg_BD2210, Avg_BD1900
    ```

---

### 5) `CRISM_data_percentage`
**Purpose:** Convert the per-cell averages to **relative percentages (0–100)** per index, normalized by the **global min/max** over the cropped mosaic.

- **Inputs**
  - `mesh_mineral_averages.csv` from step 4.

- **Processing details**
  - Normalize each column (`Avg_*`) to [0–1] using global min/max; scale to **%**:
    - `% Fe/Mg`  ← normalized D2300 × 100  
    - `% Al-OH`  ← normalized BD2210 × 100  
    - `% H2O`    ← normalized BD1900 × 100
  - If a row had **all three averages = 0**, set the three % to **0**.
  - Save: **`mesh_mineral_averages_percentages.csv`** (contains both averages and percentages).

> These are **relative** percentages for visualization/comparison, **not absolute abundances**.

---

## Prerequisites

- **Python** ≥ 3.10  
- Suggested packages:
  - `rasterio==1.3.10`, `numpy`, `matplotlib`, `pyproj`
  - `geopandas`, `shapely` (only if you use vector ROIs)
- Recommended env var: `PROJ_IGNORE_CELESTIAL_BODY=YES`

---

## Configuration

Edit the configuration section before running step 1:

- `SR_PATHS`: list of `*_sr*_mtr3.img` / `*_su*_mtr3.img`
- `OUT_DIR`: output directory for PNG/TIFF/CSV
- `TARGET_RES_M`: mosaic resolution (default **200**)
- **Crop box (deg)**: `crop_lon_min`, `crop_lat_min`, `crop_lon_max`, `crop_lat_max`
- `BAND_ALIASES`: keep defaults unless you need to add vendor aliases for the three indices

---

## Outputs (summary)

- **Per scene:** `<scene>_RGB.png`, `<scene>_indices_eqc.tif`  
- **Mosaic:** `jezero_CRISM_RGB_mosaic.png`, `jezero_CRISM_indices_mosaic.tif`, `jezero_CRISM_RGB_mosaic_meshed.png`  
- **Tables:** `mesh_mineral_averages.csv`, `mesh_mineral_averages_percentages.csv`

---

## Troubleshooting

- **No CRS / reprojection issues:** input SR/SU can lack CRS; the pipeline assigns **Mars geographic** before reprojection to EQC.
- **Seams/holes in mosaic:** `method='max'` is used; try `median` or `first` if you prefer different behavior.
- **Blank areas:** alpha is applied where **all three bands** are invalid; check the footprint masking logic or your crop.
- **Memory:** lower `TARGET_RES_M` (e.g., 200→300 m) or reduce the number of scenes.

---

## Scientific context (short)

- **D2300 (~2.3 μm):** Fe/Mg smectites  
- **BD2210 (~2.21 μm):** Al-OH clays  
- **BD1900 (~1.9 μm):** hydrated phases / H₂O  
Their RGB combination visualizes the relative intensity and mixing of hydrated mineral groups.
