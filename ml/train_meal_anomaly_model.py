"""
Isolation Forest for MEAL-SERVING anomalies, Smart School Feeding Management System.

Unlike train_isolation_forest.py (which scores M-Pesa top-ups), this model
scores each served meal on five features: cost, hour of day, weekday, how many
meals that student has had that day, and how far the cost is from that
student's usual. The feature code is shared with the live backend
(backend/anomalies/meal_detection.py), so training and serving agree.

Training is unsupervised. The database holds no labelled meal anomalies, so
the model is EVALUATED on a held-out slice of real meals with synthetic
anomalies injected (meals at night, on weekends, or at 4-8x the usual cost).

Important limit of the model: an Isolation Forest can only isolate values that
vary in its training data. Seeded meals never happen at night or on weekends,
so the model cannot flag them; the explainable rules in meal_detection.py do.
The deployed detector uses both, so this script reports the model alone AND the
combined detector, per anomaly type. Run from inside ml/:

    python train_meal_anomaly_model.py
"""
import json
import os
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (f1_score, precision_score, recall_score,
                             roc_auc_score)
from sklearn.preprocessing import StandardScaler

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django  # noqa: E402

django.setup()

from anomalies.meal_detection import (FEATURES, _rule_hits,  # noqa: E402
                                      build_feature_frame)

RANDOM_STATE = 42
CONTAMINATION = 0.003
MODELS_DIR = os.path.join(HERE, 'models')

print('Loading meal events from the database...')
frame = build_feature_frame()
if len(frame) < 500:
    sys.exit(f'Only {len(frame)} meal events; need at least 500 to train.')
print(f'Loaded {len(frame)} meals')


KINDS = ['night', 'weekend', 'cost']


def inject_anomalies(rows, rng):
    """Copy random real rows and turn each into one kind of unusual meal."""
    n = max(30, int(len(rows) * 0.03))
    base = rows.sample(n=n, replace=True, random_state=RANDOM_STATE).reset_index(drop=True)
    kinds = rng.integers(0, len(KINDS), size=n)
    base['kind'] = [KINDS[k] for k in kinds]
    for i, kind in enumerate(kinds):
        if kind == 0:      # in the night / evening
            hour = int(rng.choice([0, 1, 2, 3, 4, 5, 19, 20, 21, 22, 23]))
            base.loc[i, 'hour_of_day'] = hour
            base.loc[i, 'time_label'] = f'{hour:02d}:30'
        elif kind == 1:    # weekend
            base.loc[i, 'day_of_week'] = int(rng.choice([5, 6]))
        else:              # far costlier than usual
            usual = base.loc[i, 'usual_cents']
            usual = usual if pd.notna(usual) and usual > 0 else base.loc[i, 'amount_cents']
            amount = int(usual * rng.uniform(4, 8))
            base.loc[i, 'amount_cents'] = amount
            base.loc[i, 'usual_cents'] = usual
            base.loc[i, 'amount_deviation'] = round(abs(amount - usual) / max(usual, 1), 4)
    base['is_anomaly'] = 1
    return base


# Hold out 20% of real meals for evaluation; train on the rest.
shuffled = frame.sample(frac=1.0, random_state=RANDOM_STATE).reset_index(drop=True)
split = int(len(shuffled) * 0.8)
train, test = shuffled.iloc[:split].copy(), shuffled.iloc[split:].copy()
test['is_anomaly'] = 0
rng = np.random.default_rng(RANDOM_STATE)
injected = inject_anomalies(test, rng)
evaluation = pd.concat([test, injected], ignore_index=True)

scaler = StandardScaler().fit(train[FEATURES].to_numpy(dtype=float))
model = IsolationForest(n_estimators=100, max_samples=min(256, len(train)),
                        contamination=CONTAMINATION, random_state=RANDOM_STATE)
model.fit(scaler.transform(train[FEATURES].to_numpy(dtype=float)))

scaled_eval = scaler.transform(evaluation[FEATURES].to_numpy(dtype=float))
y_true = evaluation['is_anomaly'].to_numpy()
y_pred = (model.predict(scaled_eval) == -1).astype(int)
scores = model.decision_function(scaled_eval)

rule_pred = np.array([1 if _rule_hits(row) else 0 for _, row in evaluation.iterrows()])
combined_pred = np.maximum(y_pred, rule_pred)
kind_col = evaluation['kind'].fillna('real')


def summarise(pred):
    return {
        'precision': round(float(precision_score(y_true, pred, zero_division=0)), 4),
        'recall': round(float(recall_score(y_true, pred, zero_division=0)), 4),
        'f1': round(float(f1_score(y_true, pred, zero_division=0)), 4),
        'real_meals_flagged_pct': round(float(pred[y_true == 0].mean()) * 100, 2),
        'recall_by_type': {k: round(float(pred[(kind_col == k).to_numpy()].mean()), 4)
                           for k in KINDS},
    }


model_only = summarise(y_pred)
model_only['auc_roc'] = round(float(roc_auc_score(y_true, -scores)), 4)
combined = summarise(combined_pred)

print('\n' + '=' * 50)
print('MEAL ANOMALY EVALUATION (held-out meals + injected anomalies)')
print('=' * 50)
print(f'Held-out real meals: {len(test)}   Injected anomalies: {len(injected)}')
for label, m in (('Model alone', model_only), ('Model + rules', combined)):
    print(f"{label:14} precision {m['precision']:.3f}  recall {m['recall']:.3f}  "
          f"F1 {m['f1']:.3f}  real meals flagged {m['real_meals_flagged_pct']:.2f}%")
    print(f"{'':14} recall by type: {m['recall_by_type']}")

# Deployed model: refit on ALL real meals.
final_scaler = StandardScaler().fit(frame[FEATURES].to_numpy(dtype=float))
final_model = IsolationForest(n_estimators=100, max_samples=min(256, len(frame)),
                              contamination=CONTAMINATION, random_state=RANDOM_STATE)
final_model.fit(final_scaler.transform(frame[FEATURES].to_numpy(dtype=float)))
joblib.dump(final_model, os.path.join(MODELS_DIR, 'meal_isolation_forest.joblib'))
joblib.dump(final_scaler, os.path.join(MODELS_DIR, 'scaler_meal.joblib'))

report = {
    'model': 'Isolation Forest (meal serving)',
    'features': FEATURES,
    'parameters': {'n_estimators': 100, 'contamination': CONTAMINATION,
                   'random_state': RANDOM_STATE},
    'dataset': {
        'total_meals': int(len(frame)),
        'train_meals': int(len(train)),
        'held_out_meals': int(len(test)),
        'injected_anomalies': int(len(injected)),
        'injected_types': KINDS,
    },
    'metrics': {'model_alone': model_only, 'model_plus_rules': combined},
    'caution': ('The database has no labelled meal anomalies, so the evaluation '
                'injects synthetic ones (night or weekend meals, 4-8x the usual '
                'cost) into held-out real meals. The model alone cannot flag '
                'night or weekend meals because the training data contains none, '
                'so the deployed detector adds explainable rules for them. The '
                'scores show it separates obvious outliers, not how it performs '
                'on real misuse.'),
}
with open(os.path.join(MODELS_DIR, 'meal_anomaly_evaluation.json'), 'w', encoding='utf-8') as fh:
    json.dump(report, fh, indent=2, ensure_ascii=False)
print('\nSaved meal_isolation_forest.joblib, scaler_meal.joblib, meal_anomaly_evaluation.json')
