# Owner: Zuzanna Jacyna
# Affiliation: Politechnika Warszawska
# Last update: 13/11/2025


import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

import matplotlib.pyplot as plt


# ================================
# 1. Load data
# ================================
# --- 1. Load and Filter Data ---
data = pd.read_csv("/content/jezero_final_ML.csv")

# Define the columns for filtering
cols_to_check = ['% Fe/Mg', '% Al-OH', '% H2O']

# Create a Boolean mask to identify rows where ALL three columns are 0.00
rows_to_drop_mask = (
    (data[cols_to_check[0]] == 0.00) &
    (data[cols_to_check[1]] == 0.00) &
    (data[cols_to_check[2]] == 0.00)
)

# Filter the data: keep only the rows that are NOT in the mask
data_filtered = data[~rows_to_drop_mask].copy()

print(f"Original rows: {len(data)}, Filtered rows: {len(data_filtered)}")

# --- 2. Define Features (X) and Target (y) ---
# Drop the target and the coordinate columns 'x' and 'y' from the feature matrix X
columns_to_drop = ["good_landing_place", "x", "y"]
X = data_filtered.drop(columns_to_drop, axis=1)
y = data_filtered["good_landing_place"]
# ================================
# 2. Train/test split
# ================================
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y  # CRUCIAL for maintaining class proportion
)


# ================================
# 3. Scale
# ================================
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)


# ================================
# 4. Model
# ================================
model = LogisticRegression(class_weight="balanced", max_iter=200)
model.fit(X_train_scaled, y_train)

y_pred = model.predict(X_test_scaled)
y_proba = model.predict_proba(X_test_scaled)[:, 1]

print("Accuracy:", accuracy_score(y_test, y_pred))
print("\nConfusion matrix:\n", confusion_matrix(y_test, y_pred))
print("\nClassification report:\n", classification_report(y_test, y_pred))


# ================================
# 5. Confusion Matrix Plot
# ================================
cm = confusion_matrix(y_test, y_pred)

plt.figure(figsize=(5, 5))
plt.imshow(cm)
plt.title("Confusion Matrix")
plt.xlabel("Predicted")
plt.ylabel("Actual")

for i in range(cm.shape[0]):
    for j in range(cm.shape[1]):
        plt.text(j, i, str(cm[i, j]), ha="center", va="center")

plt.savefig("confusion_matrix.png", dpi=300, bbox_inches="tight")
plt.close()

from sklearn.metrics import roc_curve, auc

# ================================
# 6. ROC Curve Plot
# ================================

# Calculate ROC curve
fpr, tpr, thresholds = roc_curve(y_test, y_proba)
roc_auc = auc(fpr, tpr)

plt.figure(figsize=(6, 6))
plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (area = {roc_auc:.2f})')
plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('Receiver Operating Characteristic (ROC) Curve')
plt.legend(loc="lower right")
plt.grid(True)
plt.savefig("roc_curve.png", dpi=300, bbox_inches="tight")
plt.close()

from sklearn.metrics import precision_recall_curve, PrecisionRecallDisplay

# ================================
# 7. Precision-Recall Curve Plot
# ================================

# Calculate Precision-Recall curve
precision, recall, _ = precision_recall_curve(y_test, y_proba)

# Plot the Precision-Recall curve
disp = PrecisionRecallDisplay(precision=precision, recall=recall)
disp.plot()
plt.title('Precision-Recall Curve')
plt.grid(True)
plt.savefig("precision_recall_curve.png", dpi=300, bbox_inches="tight")
plt.close()

# ================================
# 8. Feature Importance Plot
# ================================
coeffs = model.coef_[0]
features = X.columns

plt.figure(figsize=(10, 6))
plt.barh(features, coeffs)
plt.title("Feature Importance (Logistic Regression Coefficients)")
plt.xlabel("Coefficient Value")
plt.ylabel("Feature")
plt.tight_layout()
plt.savefig("feature_importance.png", dpi=300, bbox_inches="tight")
plt.close()

import seaborn as sns

# ================================
# 9. Correlation Heatmap Plot
# ================================

# Calculate the correlation matrix
correlation_matrix = X.corr()

plt.figure(figsize=(10, 8))
sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', fmt=".2f")
plt.title('Correlation Heatmap of Features')
plt.tight_layout()
plt.savefig("correlation_heatmap.png", dpi=300, bbox_inches="tight")
plt.close()

# ================================
# 10. Print outputs
# ================================

print("All plots saved:")
print(" - confusion_matrix.png")
print(" - roc_curve.png")
print(" - precision_recall_curve.png")
print(" - feature_importance.png")
print(" - correlation_heatmap.png")

# ================================
# 1!. Print some numbers
# ================================

import pandas as pd

# Load the CSV file. 
file_path = "/content/jezero_final_ML.csv"
data = pd.read_csv(file_path)

print(f"Number of samples available for training: {len(X_train)}")
print(f"Number of samples available for testing: {len(X_test)}")

good_landing_spots = data['good_landing_place'].sum()
print(f"Number of good spot landings in '{file_path}': {int(good_landing_spots)}")

num_good_landing_test = y_test.sum()
print(f"Number of samples in the test set with 'good_landing_place = 1': {int(num_good_landing_test)}")
    
