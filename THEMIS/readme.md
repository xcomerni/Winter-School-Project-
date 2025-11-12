# THEMIS SUMMARY

## Code Summary
This code processes THEMIS XML metadata and image data to analyze surface temperatures over Jezero across different Local Solar Times (LST), producing mosaics, a 100×100 aggregated grid, diagnostics, and ML-ready tables.

## Main Steps
1. **LST Indexing** – Extract LST from PDS4 XML (`themis_lst_index.csv`) to organize by time of day.
2. **Mosaicking & Reprojection** – Build median BT mosaics per time window on a common Mars EQC grid; apply georeferencing and scale/offset.
3. **High-Res Outputs** – Save median BT mosaics and coverage counts as GeoTIFF + PNG.
4. **Aggregated Grid (100×100)** – Resample to coarser 100×100 grids per fascia and save GeoTIFFs + PNGs.
5. **Aggregated Visualization** – Show gridded distribution with numeric axes (0–99 for X/Y).
6. **Summary Charts** – Temperature histograms per fascia; bar chart of mean temperatures across fascias.
7. **ML Export** – `themis_ML_data_100x100.csv` with `(x, y)` and per-fascia mean temperatures.
8. **Operational Flags (per timeslot)** – `themis_timeslot_flags_ops.csv` adds per-cell/per-slot flags for THEMIS data quality, rover (strict/soft), and helicopter (survival/energy).
9. **Operational Zone Maps** – 100×100 plots per fascia: *Bad* / *Good Soft Only* / *Good Strict*.
10. **Zone Distribution** – Grouped bar chart of operational classes across fascias.
11. **ML Flags-Only** – `themis_ml_flags_only.csv` with unified status flags per fascia.

## Outputs (selection)
- **themis_BT_{time}_median.tif/png** – Median BT mosaics per fascia; **themis_BT_{time}_count.tif** for coverage.
- **themis_BT_Grid100x100_{time}_median.tif/png** – 100×100 aggregated grids (with 0–99 axes).
- **themis_TempHist_Grid100x100_{time}.png**, **themis_MeanTemp_Grid100x100_BarChart.png** – Diagnostics.
- **themis_ML_data_100x100.csv** – ML table with timeslot means.
- **themis_timeslot_flags_ops.csv** – Per-slot operational flags + reasons.
- **themis_OperationalZones_{time}.png**, **themis_OperationalZoneDistribution.png** – Operational maps & counts.

## THEMIS — “When” to operate (per-timeslot thermal sanity + rover/heli)

### (a) Per-timeslot data quality (THEMIS)
Outlier filtering per slot with **p10–p90** band, clipped to **[−120, +20] °C**.  
→ `THEMIS_OK_<slot>`, `THEMIS_reason_<slot>` (“missing_data”, “too_cold_outlier”, “too_warm_outlier”, “good”).

### (b) Rover operational limits (environmental)
- Preferred component environment: **−40…+40 °C**.  
- Acceptable with heaters (conservative): **≥ −100 °C**.  
- **Strict, energy-aware lower bound by slot:**  
  **morning (05:30, 07:00) ≥ −70 °C; evening (18:30, 19:00) ≥ −60 °C**.  
→ `ROVER_OK_strict_<slot>`, `ROVER_OK_soft_<slot>`, `ROVER_reason_<slot>` (“ideal”, “energy_pref_slot”, “heater_needed”, “too_cold”, “too_hot”, “missing”).

### (c) Helicopter (Ingenuity-like) limits
- **Survival:** `T ≥ −100 °C`.  
- **Energy preference:** `T ≥ −70 °C`.  
→ `HELI_survival_ok_<slot>`, `HELI_energy_pref_<slot>`, `HELI_reason_<slot>` (“ok”, “cold_high_energy”, “too_cold_survival”, “missing”).

### (d) Combined per-slot decision (GOOD/BAD)
For each timeslot `<slot>`, let **T** be the brightness temperature (°C) of that slot.

**STRICT** → `SLOT_GOOD_strict_<slot> = 1` iff  
1) `THEMIS_OK_<slot> = 1` (within per-slot p10–p90, clipped to [−120, +20] °C);  
2) `T ≤ +40 °C` **and** `T ≥ strict_min_by_slot` (morning −70 °C; evening −60 °C);  
3) `T ≥ −100 °C` (helicopter survival).  
Else `0`.

**SOFT** → `SLOT_GOOD_soft_<slot> = 1` iff  
1) `THEMIS_OK_<slot> = 1`;  
2) `T ≤ +40 °C` **and** `T ≥ −100 °C` (rover soft);  
3) `T ≥ −100 °C` (helicopter survival).  
Else `0`.

*Ranking note:* `HELI_energy_pref_<slot> = 1` when `T ≥ −70 °C`.  
*Auditability:* `SLOT_REASON_strict_<slot>` / `SLOT_REASON_soft_<slot>` store the first failing constraint.
