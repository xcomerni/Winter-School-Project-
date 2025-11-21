# ML SUMMARY

## Code Summary
This script trains and evaluates a **binary classifier** for potential landing sites in Jezero crater using the fused dataset `jezero_final_ML.csv`.  
Features come from **MOLA** (slope), **THEMIS** (temperatures at different local times), and **CRISM** (hydrated mineral percentages).  
The model is a **Logistic Regression** with class balancing, returning predictions for `good_landing_place` ∈ {0, 1}.

## Code Steps
1. **Data Loading**  
   - Read the fused table:
     ```python
     data = pd.read_csv("/content/jezero_final_ML.csv")
     ```
   - Each row corresponds to one cell in the **100×100 grid** over Jezero.

2. **Filtering Invalid Mineral Cells**  
   Remove rows where all CRISM-based mineral percentages are zero:
   ```python
   cols_to_check = ['% Fe/Mg', '% Al-OH', '% H2O']
   rows_to_drop_mask = (
       (data[cols_to_check[0]] == 0.00) &
       (data[cols_to_check[1]] == 0.00) &
       (data[cols_to_check[2]] == 0.00)
   )
   data_filtered = data[~rows_to_drop_mask].copy()
