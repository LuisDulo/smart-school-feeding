"""
Random Forest Regressor for demand forecasting.
Smart School Feeding Management System — Luis Enrique Okal Dulo

Algorithm: Random Forest (Breiman, 2001)
- Ensemble of 200 decision trees
- Bootstrap aggregating (bagging)
- Handles nonlinear feature interactions
- Provides feature importance rankings

Features: student_enrolment, attendance_rate, term_week,
          day_of_week, is_exam_week, rolling_7day_avg
Target: meals_served (continuous)
"""
import sys
import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import cross_val_score, KFold
from sklearn.metrics import (mean_absolute_error,
                              mean_squared_error, r2_score)
import joblib
import json

# Windows consoles often default to a legacy codepage (e.g. cp1252) that
# can't encode the arrows/bars/checkmarks below and would crash mid-run —
# force UTF-8 so this runs the same everywhere.
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 60)
print("RANDOM FOREST REGRESSOR — DEMAND FORECASTING")
print("Smart School Feeding Management System")
print("=" * 60)

# ── Load data ─────────────────────────────────────────────────────
csv_path = os.path.join('data', 'meal_distribution.csv')
df = pd.read_csv(csv_path)
print(f"\nDataset: {len(df)} rows loaded from {csv_path}")
print(f"Date range: {df['meal_date'].min()} → {df['meal_date'].max()}")
print(f"Target range: {df['meals_served'].min()} – "
      f"{df['meals_served'].max()} meals/day")

# ── Features ──────────────────────────────────────────────────────
FEATURES = [
    'student_enrolment',
    'attendance_rate',
    'term_week',
    'day_of_week',
    'is_exam_week',
    'rolling_7day_avg'
]
TARGET = 'meals_served'

X = df[FEATURES].values
y = df[TARGET].values

# ── Chronological split — NO shuffle (prevents data leakage) ──────
split_idx = int(len(X) * 0.8)
X_train, X_test = X[:split_idx], X[split_idx:]
y_train, y_test = y[:split_idx], y[split_idx:]
print(f"\nTrain: {len(X_train)} rows | Test: {len(X_test)} rows")
print("Split: chronological (no shuffle) — prevents data leakage")

# ── Scale features ────────────────────────────────────────────────
scaler = MinMaxScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

# ── Train Random Forest ───────────────────────────────────────────
print("\nTraining Random Forest Regressor...")
print("  n_estimators=200, max_depth=None (fully grown trees)")
print("  min_samples_split=5, min_samples_leaf=2")
print("  bootstrap=True, random_state=42")

rf_model = RandomForestRegressor(
    n_estimators=200,
    max_depth=None,
    min_samples_split=5,
    min_samples_leaf=2,
    n_jobs=-1,
    bootstrap=True,
    random_state=42
)
rf_model.fit(X_train_s, y_train)
print("Training complete.")

# ── Evaluate on test set ──────────────────────────────────────────
y_pred = rf_model.predict(X_test_s)
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)

print("\n" + "=" * 60)
print("RANDOM FOREST — TEST SET RESULTS")
print("=" * 60)
print(f"MAE:   {mae:.4f} meals/day")
print(f"RMSE:  {rmse:.4f} meals/day")
print(f"R²:    {r2:.4f}")

# ── 5-fold cross-validation ───────────────────────────────────────
print("\nRunning 5-fold cross-validation...")
kf = KFold(n_splits=5, shuffle=False)
X_scaled_full = scaler.fit_transform(X)
cv_mae = cross_val_score(
    RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1),
    X_scaled_full, y,
    cv=kf, scoring='neg_mean_absolute_error')
cv_r2 = cross_val_score(
    RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1),
    X_scaled_full, y,
    cv=kf, scoring='r2')
print(f"CV MAE: {-cv_mae.mean():.4f} ± {cv_mae.std():.4f}")
print(f"CV R²:  {cv_r2.mean():.4f} ± {cv_r2.std():.4f}")

# ── Feature importance ────────────────────────────────────────────
importances = rf_model.feature_importances_
print("\nFeature Importances (Random Forest):")
print("-" * 45)
sorted_idx = np.argsort(importances)[::-1]
for i in sorted_idx:
    bar = "█" * int(importances[i] * 40)
    print(f"  {FEATURES[i]:25s} {bar} {importances[i]:.4f}")

# ── Save model, scaler, and metrics ──────────────────────────────
os.makedirs('models', exist_ok=True)
joblib.dump(rf_model, 'models/random_forest.joblib')
joblib.dump(scaler, 'models/scaler_rf.joblib')

metrics = {
    'model': 'Random Forest Regressor',
    'algorithm': 'Ensemble — Bootstrap Aggregating (Bagging)',
    'n_estimators': 200,
    'features': FEATURES,
    'train_rows': len(X_train),
    'test_rows': len(X_test),
    'mae': round(mae, 4),
    'rmse': round(rmse, 4),
    'r2': round(r2, 4),
    'cv_mae_mean': round(-cv_mae.mean(), 4),
    'cv_mae_std': round(cv_mae.std(), 4),
    'cv_r2_mean': round(cv_r2.mean(), 4),
    'feature_importances': {
        FEATURES[i]: round(float(importances[i]), 4)
        for i in range(len(FEATURES))
    }
}
with open('models/rf_metrics.json', 'w') as f:
    json.dump(metrics, f, indent=2)

print("\n✅ Random Forest model saved:")
print("   ml/models/random_forest.joblib")
print("   ml/models/scaler_rf.joblib")
print("   ml/models/rf_metrics.json")
