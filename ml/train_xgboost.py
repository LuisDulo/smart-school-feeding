"""
XGBoost Regressor for demand forecasting.
Smart School Feeding Management System — Luis Enrique Okal Dulo

Algorithm: XGBoost (Chen & Guestrin, 2016)
- Gradient boosting framework
- Sequentially builds trees where each tree corrects
  the residual errors of the previous trees
- L1 and L2 regularisation to prevent overfitting
- Winner of most Kaggle tabular data competitions 2016-2022

Features: student_enrolment, attendance_rate, term_week,
          day_of_week, is_exam_week, rolling_7day_avg
Target: meals_served (continuous)
"""
import sys
import os
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import cross_val_score, KFold
from sklearn.metrics import (mean_absolute_error,
                              mean_squared_error, r2_score)
import joblib
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 60)
print("XGBOOST REGRESSOR — DEMAND FORECASTING")
print("Smart School Feeding Management System")
print("=" * 60)
print(f"XGBoost version: {xgb.__version__}")

# ── Load data ─────────────────────────────────────────────────────
csv_path = os.path.join('data', 'meal_distribution.csv')
df = pd.read_csv(csv_path)
print(f"\nDataset: {len(df)} rows")
print(f"Date range: {df['meal_date'].min()} → {df['meal_date'].max()}")

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

# ── Chronological split ───────────────────────────────────────────
split_idx = int(len(X) * 0.8)
X_train, X_test = X[:split_idx], X[split_idx:]
y_train, y_test = y[:split_idx], y[split_idx:]
print(f"\nTrain: {len(X_train)} rows | Test: {len(X_test)} rows")

# ── Scale features ────────────────────────────────────────────────
scaler = MinMaxScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

# ── XGBoost with early stopping ───────────────────────────────────
# Use last 20% of training data as validation for early stopping
val_split = int(len(X_train_s) * 0.8)
X_tr = X_train_s[:val_split]
X_val = X_train_s[val_split:]
y_tr = y_train[:val_split]
y_val = y_train[val_split:]

print("\nTraining XGBoost Regressor...")
print("  n_estimators=500 (with early stopping)")
print("  learning_rate=0.05, max_depth=6")
print("  subsample=0.8, colsample_bytree=0.8")
print("  reg_alpha=0.1 (L1), reg_lambda=1.0 (L2)")

xgb_model = xgb.XGBRegressor(
    n_estimators=500,
    learning_rate=0.05,
    max_depth=6,
    min_child_weight=3,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_alpha=0.1,
    reg_lambda=1.0,
    objective='reg:squarederror',
    eval_metric='mae',
    early_stopping_rounds=30,
    random_state=42,
    n_jobs=-1,
    verbosity=0
)

xgb_model.fit(
    X_tr, y_tr,
    eval_set=[(X_val, y_val)],
    verbose=False
)
best_iter = xgb_model.best_iteration
print(f"Best iteration: {best_iter} (early stopping active)")

# ── Evaluate ──────────────────────────────────────────────────────
y_pred = xgb_model.predict(X_test_s)
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)

print("\n" + "=" * 60)
print("XGBOOST — TEST SET RESULTS")
print("=" * 60)
print(f"MAE:   {mae:.4f} meals/day")
print(f"RMSE:  {rmse:.4f} meals/day")
print(f"R²:    {r2:.4f}")
print(f"Trees used: {best_iter + 1} (of 500 max)")

# ── 5-fold cross-validation ───────────────────────────────────────
print("\nRunning 5-fold cross-validation...")
kf = KFold(n_splits=5, shuffle=False)
X_scaled_full = scaler.fit_transform(X)

xgb_cv = xgb.XGBRegressor(
    n_estimators=best_iter + 1,
    learning_rate=0.05,
    max_depth=6,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    n_jobs=-1,
    verbosity=0
)
cv_mae = cross_val_score(
    xgb_cv, X_scaled_full, y,
    cv=kf, scoring='neg_mean_absolute_error')
cv_r2 = cross_val_score(
    xgb_cv, X_scaled_full, y,
    cv=kf, scoring='r2')
print(f"CV MAE: {-cv_mae.mean():.4f} ± {cv_mae.std():.4f}")
print(f"CV R²:  {cv_r2.mean():.4f} ± {cv_r2.std():.4f}")

# ── Feature importance ────────────────────────────────────────────
importances = xgb_model.feature_importances_
print("\nFeature Importances (XGBoost — gain-based):")
print("-" * 45)
sorted_idx = np.argsort(importances)[::-1]
for i in sorted_idx:
    bar = "█" * int(importances[i] * 40)
    print(f"  {FEATURES[i]:25s} {bar} {importances[i]:.4f}")

# ── Save model, scaler, and metrics ──────────────────────────────
os.makedirs('models', exist_ok=True)
joblib.dump(xgb_model, 'models/xgboost_regressor.joblib')
joblib.dump(scaler, 'models/scaler_xgb.joblib')

metrics = {
    'model': 'XGBoost Regressor',
    'algorithm': 'Gradient Boosting (Chen & Guestrin, 2016)',
    'n_estimators_used': best_iter + 1,
    'n_estimators_max': 500,
    'learning_rate': 0.05,
    'max_depth': 6,
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
with open('models/xgb_metrics.json', 'w') as f:
    json.dump(metrics, f, indent=2)

print("\n✅ XGBoost model saved:")
print("   ml/models/xgboost_regressor.joblib")
print("   ml/models/scaler_xgb.joblib")
print("   ml/models/xgb_metrics.json")
