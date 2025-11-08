# CRISM — Workflow & Dataset

This README documents the contents of the `CRISM` folder in the repository and the **execution flow** of the codes.  
The goal is to generate RGB visualizations, 3D meshes, extract spectral indices for regions of interest, and compute percentages/coverage.

---

## Execution order

1. `CRISM_RGB`
2. `CRISM_mesh`
3. `CRISM_mesh_axis`
4. `CRISM_data`
5. `CRISM_data_percentage`

> Each script consumes outputs from the previous step (when applicable). Follow the order above.

---

## Contents

- **Codes**
  - `CRISM_RGB.py`: builds RGB composites from CRISM cubes.
  - `CRISM_mesh.py`: generates 3D mesh/scene or index surface (e.g., heightmap/heatmap).
  - `CRISM_mesh_axis.py`: adds/optimizes axes and annotations to the mesh.
  - `CRISM_data.py`: extracts spectral indices/metrics per region of interest.
  - `CRISM_data_percentage.py`: computes percentages/coverage of classes/indices per region.
- **Expected data**
  - CRISM **TRR3** cubes: `.img` + `.lbl`.
  - (Optional) Shapefile/GeoJSON with **regions of interest** (polygons).
  - (Optional) Auxiliary files (wavelengths, masks, DEM).

---

## Prerequisites

- **Python** ≥ 3.10  
- Typical packages (adapt to your setup):
  - `numpy`, `pandas`, `matplotlib`
  - `rasterio` and/or `GDAL`
  - `geopandas`, `shapely`
  - `pvl` (to read `.lbl` labels)
  - `scikit-image` (optional, for filters/masks)
  - `spectral` (optional, for hyperspectral ops)

> Install dependencies via `pip install -r requirements.txt` if available, otherwise install manually.

---

## Recommended folder layout

