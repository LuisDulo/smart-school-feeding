"""
Linear Regression demand forecasting model for
Smart School Feeding Management System.
Target: predict daily meals served.
Features: enrolment, attendance_rate, term_week,
          day_of_week, is_exam_week, rolling_7day_avg
"""
import sys
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import os

# Windows consoles often default to a legacy codepage (e.g. cp1252) that
# can't encode the arrows/checkmarks below and would crash mid-run —
# force UTF-8 so this runs the same everywhere.
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# ── Load data ─────────────────────────────────────────────────────
csv_path = os.path.join('data', 'meal_distribution.csv')
df = pd.read_csv(csv_path)
print(f"Loaded {len(df)} rows from {csv_path}")
print(df.head())
print(f"\nColumns: {list(df.columns)}")
print(f"Date range: {df['meal_date'].min()} → {df['meal_date'].max()}")

# ── Feature engineering ───────────────────────────────────────────
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

print(f"\nFeature matrix shape: {X.shape}")
print(f"Target shape:         {y.shape}")
print(f"Target range:         {y.min()} – {y.max()} meals/day")

# ── Chronological train/test split (NO shuffle — prevents leakage) ──
split_idx = int(len(X) * 0.8)
X_train, X_test = X[:split_idx], X[split_idx:]
y_train, y_test = y[:split_idx], y[split_idx:]
print(f"\nTrain rows: {len(X_train)} | Test rows: {len(X_test)}")

# ── Scale features ────────────────────────────────────────────────
scaler = MinMaxScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s  = scaler.transform(X_test)

# ── Train model ───────────────────────────────────────────────────
model = LinearRegression()
model.fit(X_train_s, y_train)

# ── Evaluate ──────────────────────────────────────────────────────
y_pred = model.predict(X_test_s)
mae    = mean_absolute_error(y_test, y_pred)
rmse   = np.sqrt(mean_squared_error(y_test, y_pred))
r2     = r2_score(y_test, y_pred)

print("\n" + "="*50)
print("MODEL EVALUATION RESULTS")
print("="*50)
print(f"MAE:   {mae:.2f} meals/day  (target: < 15)")
print(f"RMSE:  {rmse:.2f} meals/day")
print(f"R²:    {r2:.4f}            (target: > 0.70)")

# Cross validation
cv_scores = cross_val_score(
    LinearRegression(),
    scaler.fit_transform(X), y,
    cv=5, scoring='neg_mean_absolute_error'
)
print(f"5-fold CV MAE: {-cv_scores.mean():.2f} ± {cv_scores.std():.2f}")

# Feature coefficients
print("\nFeature coefficients:")
for feat, coef in zip(FEATURES, model.coef_):
    print(f"  {feat:25s}: {coef:+.4f}")
print(f"  {'Intercept':25s}: {model.intercept_:+.4f}")

# ── Save model and scaler ─────────────────────────────────────────
os.makedirs('models', exist_ok=True)
joblib.dump(model,  'models/linear_regression.joblib')
joblib.dump(scaler, 'models/scaler_lr.joblib')

print("\n✅ Models saved:")
print("   ml/models/linear_regression.joblib")
print("   ml/models/scaler_lr.joblib")
print("\nReady for Sprint 4 forecasting API.")
