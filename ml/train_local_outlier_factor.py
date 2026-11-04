"""
Local Outlier Factor anomaly detection model for
Smart School Feeding Management System.

Algorithm: LocalOutlierFactor (Breunig, Kriegel, Ng & Sander, 2000), run in
           novelty mode so the fitted model can score new transactions.
Idea:      a transaction is anomalous if its local density is much lower than
           the density of its nearest neighbours (a "density-based" detector,
           in contrast to the Isolation Forest's random-partitioning approach).
Features:  same seven transaction features as the Isolation Forest
           (see anomaly_features.py)
Target:    unsupervised — labels are used only to report metrics
Output:    models/local_outlier_factor.joblib, models/scaler_lof.joblib
"""
import os
import sys

import joblib
import numpy as np
from sklearn.metrics import (confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from anomaly_features import FEATURES, load_feature_frame

df = load_feature_frame()

X = df[FEATURES].values
y_true = df['is_anomaly'].values  # used only for evaluation

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Same threshold rule as the Isolation Forest: a small margin above the known
# synthetic anomaly rate, never below 1%.
contamination = max(0.01, round(df['is_anomaly'].mean() + 0.005, 4))
N_NEIGHBORS = 20
print(f"\nTraining Local Outlier Factor (n_neighbors={N_NEIGHBORS}, "
      f"contamination={contamination})...")

lof = LocalOutlierFactor(
    n_neighbors=min(N_NEIGHBORS, len(X) - 1),
    contamination=contamination,
    novelty=True,
)
lof.fit(X_scaled)

scores = lof.decision_function(X_scaled)
y_pred = (lof.predict(X_scaled) == -1).astype(int)

print("\n" + "=" * 50)
print("LOCAL OUTLIER FACTOR EVALUATION (fit and scored on all data)")
print("=" * 50)
if y_true.sum() > 0:
    print(f"Precision:  {precision_score(y_true, y_pred, zero_division=0):.4f}")
    print(f"Recall:     {recall_score(y_true, y_pred, zero_division=0):.4f}")
    print(f"F1-score:   {f1_score(y_true, y_pred, zero_division=0):.4f}")
    try:
        print(f"AUC-ROC:    {roc_auc_score(y_true, -scores):.4f}")
    except Exception:
        print("AUC-ROC:    N/A")
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    print(f"\nTN={tn}  FP={fp}  FN={fn}  TP={tp}")
else:
    print(f"Flagged as anomalous: {y_pred.sum()} / {len(y_pred)} transactions")
print("(For the fair head-to-head with the Isolation Forest on held-out data, "
      "run compare_anomaly_models.py)")

os.makedirs('models', exist_ok=True)
joblib.dump(lof, 'models/local_outlier_factor.joblib')
joblib.dump(scaler, 'models/scaler_lof.joblib')
print("\nModels saved:")
print("   ml/models/local_outlier_factor.joblib")
print("   ml/models/scaler_lof.joblib")
