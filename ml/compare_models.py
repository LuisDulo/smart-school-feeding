"""
Model comparison script -- all three forecasting models.
Produces a side-by-side evaluation table for Chapter 4.
Smart School Feeding Management System -- Luis Enrique Okal Dulo
"""
import sys
import os
import json
import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import (mean_absolute_error,
                              mean_squared_error, r2_score)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("MODEL COMPARISON — DEMAND FORECASTING")
print("Smart School Feeding Management System")
print("Luis Enrique Okal Dulo — Strathmore University")
print("=" * 70)

# ── Load dataset ──────────────────────────────────────────────────
csv_path = os.path.join('data', 'meal_distribution.csv')
df = pd.read_csv(csv_path)

FEATURES = [
    'student_enrolment', 'attendance_rate', 'term_week',
    'day_of_week', 'is_exam_week', 'rolling_7day_avg'
]
TARGET = 'meals_served'

X = df[FEATURES].values
y = df[TARGET].values
split_idx = int(len(X) * 0.8)
X_test = X[split_idx:]
y_test = y[split_idx:]

# ── Load all three models ─────────────────────────────────────────
models = [
    {
        'name': 'Linear Regression',
        'short': 'LR',
        'type': 'Parametric',
        'model_path': 'models/linear_regression.joblib',
        'scaler_path': 'models/scaler_lr.joblib',
    },
    {
        'name': 'Random Forest',
        'short': 'RF',
        'type': 'Ensemble (Bagging)',
        'model_path': 'models/random_forest.joblib',
        'scaler_path': 'models/scaler_rf.joblib',
    },
    {
        'name': 'XGBoost',
        'short': 'XGB',
        'type': 'Ensemble (Boosting)',
        'model_path': 'models/xgboost_regressor.joblib',
        'scaler_path': 'models/scaler_xgb.joblib',
    },
]

results = []
print(f"\nEvaluating on {len(X_test)} held-out test samples...\n")

for m in models:
    model = joblib.load(m['model_path'])
    scaler = joblib.load(m['scaler_path'])

    X_test_s = scaler.transform(X_test)
    y_pred = model.predict(X_test_s)

    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    mape = np.mean(np.abs(
        (y_test - y_pred) / np.maximum(y_test, 1))) * 100

    results.append({
        'name': m['name'],
        'short': m['short'],
        'type': m['type'],
        'mae': round(float(mae), 4),
        'rmse': round(float(rmse), 4),
        'r2': round(float(r2), 4),
        'mape': round(float(mape), 2),
    })

# ── Print comparison table ────────────────────────────────────────
print(f"{'Model':<22} {'Type':<25} {'MAE':>8} {'RMSE':>8} {'R²':>8} {'MAPE':>8}")
print("-" * 75)

best_mae = min(r['mae'] for r in results)
best_rmse = min(r['rmse'] for r in results)
best_r2 = max(r['r2'] for r in results)

for r in results:
    mae_str = f"{r['mae']:.4f}" + (" ✓" if r['mae'] == best_mae else "")
    rmse_str = f"{r['rmse']:.4f}" + (" ✓" if r['rmse'] == best_rmse else "")
    r2_str = f"{r['r2']:.4f}" + (" ✓" if r['r2'] == best_r2 else "")
    print(f"{r['name']:<22} {r['type']:<25} "
          f"{mae_str:>10} {rmse_str:>10} {r2_str:>10} "
          f"{r['mape']:>7.2f}%")

# ── Calculate improvements over baseline ─────────────────────────
lr = results[0]
rf = results[1]
xgb = results[2]

print("\n" + "=" * 70)
print("IMPROVEMENT OVER LINEAR REGRESSION BASELINE")
print("=" * 70)
rf_mae_imp = (lr['mae'] - rf['mae']) / lr['mae'] * 100
rf_r2_imp = (rf['r2'] - lr['r2']) / abs(lr['r2']) * 100
xgb_mae_imp = (lr['mae'] - xgb['mae']) / lr['mae'] * 100
xgb_r2_imp = (xgb['r2'] - lr['r2']) / abs(lr['r2']) * 100

print(f"Random Forest vs Linear Regression:")
print(f"  MAE improved by:  {rf_mae_imp:.1f}%")
print(f"  R²  improved by:  {rf_r2_imp:.1f}%")
print(f"\nXGBoost vs Linear Regression:")
print(f"  MAE improved by:  {xgb_mae_imp:.1f}%")
print(f"  R²  improved by:  {xgb_r2_imp:.1f}%")

# Determine winner
winner = min(results, key=lambda x: x['mae'])
print(f"\n\U0001F3C6 Best model by MAE: {winner['name']} "
      f"(MAE = {winner['mae']})")

# ── Save comparison to JSON ───────────────────────────────────────
comparison = {
    'models': results,
    'best_model': winner['name'],
    'best_mae': winner['mae'],
    'best_r2': winner['r2'],
    'improvements': {
        'rf_vs_lr_mae_pct': round(rf_mae_imp, 2),
        'rf_vs_lr_r2_pct': round(rf_r2_imp, 2),
        'xgb_vs_lr_mae_pct': round(xgb_mae_imp, 2),
        'xgb_vs_lr_r2_pct': round(xgb_r2_imp, 2),
    },
    'test_samples': len(X_test),
    'features': FEATURES,
}
with open('models/model_comparison.json', 'w') as f:
    json.dump(comparison, f, indent=2)

print("\n✅ Comparison saved to ml/models/model_comparison.json")
print("\nPaste the table above directly into Chapter 4 Section 4.3")
