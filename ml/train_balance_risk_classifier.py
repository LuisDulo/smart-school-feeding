"""
Random Forest Classifier -- Student Balance Depletion Risk.
Smart School Feeding Management System -- Luis Enrique Okal Dulo

Task: Binary classification
Label: Will this student's balance hit zero within 7 days?
  0 = Safe (balance sufficient for next 7 school days)
  1 = At Risk (balance will be depleted within 7 days)

Features derived from live database records.
"""
import sys
import os
import django
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import (train_test_split,
                                      cross_val_score,
                                      StratifiedKFold)
from sklearn.metrics import (accuracy_score, precision_score,
                              recall_score, f1_score,
                              roc_auc_score, confusion_matrix,
                              classification_report)
import joblib
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Setup Django ORM
sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from meals.models import MealAccount, MealDistributionEvent, PaymentTransaction
from django.db.models import Avg
from datetime import date, timedelta

print("=" * 60)
print("RANDOM FOREST CLASSIFIER — BALANCE DEPLETION RISK")
print("Smart School Feeding Management System")
print("=" * 60)

# ── Build feature matrix from database ───────────────────────────
print("\nExtracting features from database...")
accounts = MealAccount.objects.select_related('student').all()

rows = []
today = date.today()
meal_cost_cents = 5000  # KES 50 per meal

for account in accounts:
    # Average meals per week (last 4 weeks)
    four_weeks_ago = today - timedelta(weeks=4)
    meals_last_4w = MealDistributionEvent.objects.filter(
        meal_account=account,
        meal_date__gte=four_weeks_ago
    ).count()
    avg_meals_per_week = meals_last_4w / 4

    # Meals last week specifically
    last_week = today - timedelta(weeks=1)
    meals_last_week = MealDistributionEvent.objects.filter(
        meal_account=account,
        meal_date__gte=last_week
    ).count()

    # Days since last top-up
    last_tx = PaymentTransaction.objects.filter(
        meal_account=account,
        status='confirmed'
    ).order_by('-created_at').first()
    days_since_topup = (
        (today - last_tx.created_at.date()).days
        if last_tx else 60
    )

    # Number of top-ups in last 30 days
    last_30 = today - timedelta(days=30)
    topups_30d = PaymentTransaction.objects.filter(
        meal_account=account,
        status='confirmed',
        created_at__date__gte=last_30
    ).count()

    # Average top-up amount
    avg_topup = PaymentTransaction.objects.filter(
        meal_account=account,
        status='confirmed'
    ).aggregate(avg=Avg('amount_cents'))['avg'] or 0

    # Estimated days of meals remaining
    daily_cost = (avg_meals_per_week / 5) * meal_cost_cents
    days_remaining = (
        account.balance_cents / daily_cost
        if daily_cost > 0 else 999
    )

    # Label: at risk if estimated days remaining < 7
    at_risk = 1 if days_remaining < 7 else 0

    rows.append({
        'balance_cents': account.balance_cents,
        'balance_ksh': account.balance_cents / 100,
        'avg_meals_per_week': round(avg_meals_per_week, 2),
        'meals_last_week': meals_last_week,
        'days_since_topup': min(days_since_topup, 90),
        'topups_last_30d': topups_30d,
        'avg_topup_ksh': round(avg_topup / 100, 2),
        'estimated_days_remaining': round(days_remaining, 2),
        'at_risk': at_risk,
    })

df = pd.DataFrame(rows)
print(f"Records built: {len(df)}")
print(f"At-risk students: {df['at_risk'].sum()} "
      f"({df['at_risk'].mean()*100:.1f}%)")
print(f"Safe students:    {(1-df['at_risk']).sum()} "
      f"({(1-df['at_risk']).mean()*100:.1f}%)")

if len(df) < 20 or df['at_risk'].nunique() < 2:
    print("\nWARNING: Dataset too small or single-class for reliable "
          "training. Using synthetic augmentation for demonstration.")
    np.random.seed(42)
    n_synth = 200
    synth = pd.DataFrame({
        'balance_cents': np.random.randint(0, 200000, n_synth),
        'balance_ksh': np.random.uniform(0, 2000, n_synth),
        'avg_meals_per_week': np.random.uniform(1, 5, n_synth),
        'meals_last_week': np.random.randint(0, 5, n_synth),
        'days_since_topup': np.random.randint(0, 60, n_synth),
        'topups_last_30d': np.random.randint(0, 5, n_synth),
        'avg_topup_ksh': np.random.uniform(100, 1000, n_synth),
        'estimated_days_remaining': np.random.uniform(0, 30, n_synth),
    })
    synth['at_risk'] = (synth['estimated_days_remaining'] < 7).astype(int)
    df = pd.concat([df, synth], ignore_index=True)
    print(f"After augmentation: {len(df)} records")

# ── Features and target ───────────────────────────────────────────
FEATURES = [
    'balance_cents',
    'avg_meals_per_week',
    'meals_last_week',
    'days_since_topup',
    'topups_last_30d',
    'avg_topup_ksh',
    'estimated_days_remaining',
]
TARGET = 'at_risk'

X = df[FEATURES].values
y = df[TARGET].values

# ── Train / test split (stratified) ──────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2,
    random_state=42, stratify=y)
print(f"\nTrain: {len(X_train)} | Test: {len(X_test)}")

# ── Scale ─────────────────────────────────────────────────────────
scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

# ── Train classifier ──────────────────────────────────────────────
print("\nTraining Random Forest Classifier...")
clf = RandomForestClassifier(
    n_estimators=200,
    max_depth=8,
    min_samples_split=5,
    min_samples_leaf=2,
    class_weight='balanced',
    random_state=42,
    n_jobs=-1
)
clf.fit(X_train_s, y_train)

# ── Evaluate ──────────────────────────────────────────────────────
y_pred = clf.predict(X_test_s)
y_pred_proba = clf.predict_proba(X_test_s)[:, 1]

accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred, zero_division=0)
recall = recall_score(y_test, y_pred, zero_division=0)
f1 = f1_score(y_test, y_pred, zero_division=0)
try:
    auc = roc_auc_score(y_test, y_pred_proba)
except Exception:
    auc = None

print("\n" + "=" * 60)
print("BALANCE RISK CLASSIFIER — RESULTS")
print("=" * 60)
print(f"Accuracy:  {accuracy:.4f}")
print(f"Precision: {precision:.4f}  (of flagged, how many truly at risk)")
print(f"Recall:    {recall:.4f}    (of at-risk, how many we caught)")
print(f"F1-Score:  {f1:.4f}")
if auc:
    print(f"AUC-ROC:   {auc:.4f}")

cm = confusion_matrix(y_test, y_pred)
print(f"\nConfusion Matrix:")
print(f"  True Negatives  (correctly safe):    {cm[0][0]}")
print(f"  False Positives (false alarm):       {cm[0][1]}")
print(f"  False Negatives (missed at-risk):    {cm[1][0]}")
print(f"  True Positives  (correctly flagged): {cm[1][1]}")

print(f"\nClassification Report:")
print(classification_report(y_test, y_pred,
      target_names=['Safe', 'At Risk']))

# ── Feature importance ────────────────────────────────────────────
importances = clf.feature_importances_
print("\nFeature Importances (Balance Risk Classifier):")
print("-" * 50)
sorted_idx = np.argsort(importances)[::-1]
for i in sorted_idx:
    bar = "█" * int(importances[i] * 40)
    print(f"  {FEATURES[i]:30s} {bar} {importances[i]:.4f}")

# ── Cross-validation ──────────────────────────────────────────────
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
X_scaled_full = scaler.fit_transform(X)
cv_f1 = cross_val_score(
    RandomForestClassifier(n_estimators=200, class_weight='balanced',
                            random_state=42, n_jobs=-1),
    X_scaled_full, y,
    cv=skf, scoring='f1')
print(f"\n5-fold Stratified CV F1: "
      f"{cv_f1.mean():.4f} ± {cv_f1.std():.4f}")

# ── Save ──────────────────────────────────────────────────────────
os.makedirs('models', exist_ok=True)
joblib.dump(clf, 'models/balance_risk_classifier.joblib')
joblib.dump(scaler, 'models/scaler_risk.joblib')

metrics = {
    'model': 'Random Forest Classifier',
    'task': 'Binary Classification — Balance Depletion Risk',
    'label_definition': 'at_risk=1 if estimated_days_remaining < 7',
    'features': FEATURES,
    'n_estimators': 200,
    'class_weight': 'balanced',
    'train_samples': len(X_train),
    'test_samples': len(X_test),
    'accuracy': round(accuracy, 4),
    'precision': round(precision, 4),
    'recall': round(recall, 4),
    'f1_score': round(f1, 4),
    'auc_roc': round(auc, 4) if auc else None,
    'cv_f1_mean': round(cv_f1.mean(), 4),
    'cv_f1_std': round(cv_f1.std(), 4),
    'confusion_matrix': cm.tolist(),
    'feature_importances': {
        FEATURES[i]: round(float(importances[i]), 4)
        for i in range(len(FEATURES))
    }
}
with open('models/risk_classifier_metrics.json', 'w') as f:
    json.dump(metrics, f, indent=2)

print("\n✅ Balance Risk Classifier saved:")
print("   ml/models/balance_risk_classifier.joblib")
print("   ml/models/scaler_risk.joblib")
print("   ml/models/risk_classifier_metrics.json")
