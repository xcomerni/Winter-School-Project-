# Winter School Project – Detection of ancient water traces and optimal landing sites on Mars

This repository contains the full processing and analysis pipeline used during the **Winter School** project to evaluate potential landing sites in **Jezero crater (Mars)**.

The workflow integrates:

- **MOLA** topography (slope / roughness);
- **THEMIS** surface temperature at multiple local times;
- **CRISM** hydrated mineral indicators;
- a **Machine Learning classifier** that combines all of the above to score “good” vs “bad” landing cells on a 100×100 grid.

The code is designed primarily for exploratory analysis (e.g. Google Colab / Jupyter) and for building ML-ready tabular datasets.

---

## Repository structure

- `MOLA/`  
  Processing of MOLA DTM data:
  - reading the original PDS label (`megt44n000hb.lbl`) and raster,
  - computing **slope** and **roughness**,
  - resampling and aggregating values over a **100×100 grid** covering Jezero,
  - exporting grid-level data to CSV (`jezero.csv`, `MOLA_finalversion_ML.csv`).

- `THEMIS/`  
  Processing of THEMIS IR data:
  - ingest of PDS4 XML metadata and images,
  - grouping observations by **Local Solar Time (LST)**,
  - mosaicking brightness temperatures for each time slot,
  - reprojecting to a common EQC grid and to a **100×100 grid**,
  - computing operational flags (rover / helicopter constraints),
  - exporting ML-ready tables (`themis_ML_data_100x100.csv`, `themis_ml_flags_only.csv`,
    `themis_timeslot_flags_ops.csv`).

- `CRISM/`  
  Processing of CRISM MTRDR cubes:
  - per-scene reprojection and footprint masking,
  - mosaics of spectral indices (**BD1900, BD2210, D2300**),
  - RGB false-colour maps for hydrated minerals,
  - 100×100 grid averaging and conversion to **% Fe/Mg, % Al-OH, % H₂O**,
  - landing-spot flagging and composite scores (`CRISM_OK`, `CRISM_score`),
  - export to CSV (e.g. `mesh_mineral_averages_percentages.csv`,
    `crism_landing_flags_quantile.csv`).

- `ML/`  
  Fusion of all datasets and Machine Learning:
  - `CRISM_finalversion_ML.csv` – CRISM-only grid-level features and flags,
  - `THEMIS_finalversion_ML.csv` – THEMIS-only grid-level features and flags,
  - `MOLA_finalversion_ML.csv` – MOLA-only grid-level slope / roughness,
  - `jezero_final_ML.csv` – **merged feature table** (MOLA + THEMIS + CRISM) with
    the target label `good_landing_place`,
  - `ML.py` – training + evaluation of the ML model.

- `pipeline.md`  
  Mermaid diagram summarising the complete pipeline: raw data → per-instrument pipelines → fused ML dataset → ML model.

- `LICENSE`  
  License for this repository (see file for details).

Each subdirectory may contain its own README or comments with more technical details on the respective pipeline.

---

## Data sources

The code expects external planetary datasets (not included in this repo):

- **MOLA**: global DTM tiles (PDS), here used to derive local slope and roughness near Jezero.  
- **THEMIS IR**: Mars Odyssey THEMIS thermal infrared images with PDS4 labels (brightness temperature).  
- **CRISM**: MRO CRISM MTRDR products (`*_mtr3.img`) providing spectral indices related to hydrated minerals.

Paths in the scripts are currently configured for typical **Google Colab** setups (e.g. `/content/...` or mounted Google Drive) and will need to be adjusted for local runs.

---

## Machine Learning model

Directory: `ML/`  
Main script: `ML/ML.py`  
Main dataset: `ML/jezero_final_ML.csv`

### Features and target

`jezero_final_ML.csv` contains one row per **100×100 grid cell** over Jezero.  
The core columns are:

- Grid coordinates:
  - `x`, `y` (0–99 indices).
- **MOLA**:
  - `avg_slope` – average slope in the cell.
- **THEMIS** (temperatures in Kelvin):
  - `mean_temperature_5_30AM`,
  - `mean_temperature_7_00AM`,
  - `mean_temperature_6_30PM`,
  - `mean_temperature_7_00PM`.
- **CRISM** (normalized mineral percentages):
  - `% Fe/Mg`,
  - `% Al-OH`,
  - `% H2O`.
- Target label:
  - `good_landing_place` ∈ {0, 1}.

### Model and training

`ML.py` implements a **binary classifier**:

1. Load `jezero_final_ML.csv`.
2. Split into features `X` (all columns except `good_landing_place`) and target `y`.
3. Train/test split (80/20) using `train_test_split`.
4. Standardize features with `StandardScaler`.
5. Train a **Logistic Regression** classifier:

   ```python
   model = LogisticRegression(class_weight="balanced", max_iter=200)
