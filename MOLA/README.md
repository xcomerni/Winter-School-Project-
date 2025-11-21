# MOLA SUMMARY

## Code Summary
This script processes **MOLA DTM** data to derive **slope** and **topographic roughness** for the Jezero crater region and aggregates them on a **100×100 grid**. The result is a compact, ML-ready table (`jezero.csv` / `MOLA_finalversion_ML.csv`) with one row per grid cell and two main descriptors: `avg_slope` and `avg_roughness`.

## Code Steps
1. **Imports & Configuration**  
   Load standard libraries (`numpy`, `matplotlib`, `csv`) and geospatial tools (`gdal`, `rasterio`).  
   Define the input MOLA DTM (e.g. `megt44n000hb.lbl` / corresponding GeoTIFF) and the output folder.

2. **Crop to Jezero Crater**  
   Use a Jezero-centric bounding box in projected **meters** to:
   - open the global/large MOLA tile,
   - window the raster to the Jezero area only,
   - keep georeferencing consistent for later analysis.

3. **Pixel Scale & Mars Geometry**  
   Read the pixel spacing from the MOLA product and convert **degrees → meters** using a Mars radius.  
   This step ensures that gradients are computed in physical units (m/m) before converting to degrees.

4. **Slope Calculation**  
   - Compute `dz/dx` and `dz/dy` with `numpy.gradient`, using the meter-scale spacing.  
   - Derive the **slope** in radians and convert to **degrees**:
     \[
     \text{slope} = \arctan\left(\sqrt{(dz/dx)^2 + (dz/dy)^2}\right)
     \]
   - Mask slope values where the underlying topography is `NaN`.

5. **Roughness Calculation**  
   Apply a **moving-window filter** (via `scipy.ndimage.generic_filter`) on the elevation to quantify local topographic variability.  
   Roughness is stored as a single band expressing how “bumpy” the terrain is within each neighbourhood window.

6. **GeoTIFF Outputs (Jezero AOI)**  
   Save the Jezero-only:
   - **slope map** (degrees),  
   - **roughness map** (same grid as input MOLA),  
   as GeoTIFFs with proper georeferencing, ready for GIS visualization or further processing.

7. **100×100 Grid Aggregation**  
   - Define a **100×100 grid** over the Jezero AOI.  
   - For each cell `(x, y)`:
     - sample all MOLA slope/roughness pixels inside the cell,
     - compute `avg_slope` and `avg_roughness` (ignoring `NaN` values).

8. **CSV Export for ML**  
   Write the aggregated grid to:
   - `MOLA/jezero.csv` – base table with:
     ```text
     x, y, avg_slope, avg_roughness
     ```
   - `ML/MOLA_finalversion_ML.csv` – same structure, placed inside the ML folder as the MOLA-only feature table used in the final fusion.

## Quantities & Units
- **Slope** – degrees, derived from MOLA elevation gradients.  
- **Roughness** – unitless/local variability metric (higher = more irregular topography).  

These two descriptors are designed to be directly ingested as numerical features in the ML model (`jezero_final_ML.csv`).
