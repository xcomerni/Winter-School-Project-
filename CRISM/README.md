# CRISM SUMMARY

## Code Summary
This notebook processes CRISM spectral data for the Jezero crater to identify and quantify the relative presence of specific hydrated minerals. The pipeline spans from raw data processing to a mineral composition map optimized for ML-ready outputs.

## Code Steps
1. **Drive Mounting & Libraries** – Mount Google Drive and install `rasterio`, `geopandas`, `shapely`, `pyproj`, `matplotlib`.
2. **Per-scene Processing** – Reproject each `_sr*_mtr3.img` scene to Mars EQC @ 200 m/px, extract bands **D2300** (Fe/Mg), **BD2210** (Al-OH), **BD1900** (H₂O), apply footprint mask, and save 3-band GeoTIFF + RGB quicklook.
3. **Mosaic Creation** – Merge all reprojected scenes per band using *max* to form continuous spectral mosaics.
4. **RGB Visualization** – Build a false-color RGB (R=D2300, G=BD2210, B=BD1900), display with Lat/Lon axes, crop to Jezero AOI.
5. **Mesh (100×100) & Averaging** – Overlay a 100×100 grid; compute per-cell averages of D2300, BD2210, BD1900 (NoData→NaN→0 in the DataFrame).
6. **Mineral Percentages** – Normalize index values globally and convert to relative percentages: **% Fe/Mg**, **% Al-OH**, **% H₂O**.
7. **Data Export** – Save per-cell averages and percentages to CSV.
8. **Distributions** – Plot histograms of **% Fe/Mg**, **% Al-OH**, **% H₂O** across valid cells.
9. **Overall Composition** – Pie chart of average mineral percentages over the processed area.
10. **Landing Spot Identification (Quantiles)** – Apply **adaptive thresholds** (quantile-based) to mineral percentages and a weighted CRISM score; visualize score distribution and map “good” cells.
11. **ML Prep** – Export `(x, y, landing_flag)` using the quantile method and summarize composition of “good” cells.

## Key Outputs
- **jezero_CRISM_indices_mosaic.tif** – 3-band mosaic (D2300, BD2210, BD1900).
- **jezero_CRISM_RGB_mosaic.png** / **…_meshed.png** – False-color RGB (with alpha); version with 100×100 grid overlay.
- **mesh_mineral_averages.csv** – Per-cell `Avg_D2300`, `Avg_BD2210`, `Avg_BD1900`.
- **mesh_mineral_averages_percentages.csv** – Per-cell normalized values and **% Fe/Mg**, **% Al-OH**, **% H₂O**.
- **mineral_percentage_histograms.png**, **overall_mineral_composition_pie_chart.png** – Diagnostics and summary.
- **crism_score_distribution_quantile_histogram.png** – Score distribution under quantile thresholds.
- **crism_ok_quantile_cells_map.png** – Spatial map of *CRISM_OK* cells.
- **crism_landing_flags_quantile.csv** – `(x, y, landing_flag)` for ML.

## CRISM — “Where” to look for water (quantile-only)
**Composite score (ranking):**  
`CRISM_score = 0.60·%H2O + 0.30·%Fe/Mg + 0.10·%Al-OH`  (0–100)

**Adaptive thresholds (no fixed numbers):**
- `p80(%H2O)` → “high” H₂O (top 20%)  
- `p60(%H2O)`, `p60(%Fe/Mg)` → “medium” (top 40%)

**Decision rule (GOOD/BAD).** A cell is **GOOD** (`CRISM_OK = 1`) if:
1) it has real CRISM coverage; and  
2) **%H2O ≥ p80(%H2O)**, **or** **%H2O ≥ p60(%H2O)** **and** **%Fe/Mg ≥ p60(%Fe/Mg)**; and  
3) `CRISM_score ≥ 0.55·p80(%H2O) + 0.45·p60(%Fe/Mg)`.  
Otherwise **BAD** (`CRISM_OK = 0`).

**To the model:** provide `CRISM_OK` and `CRISM_score` (0–100).
