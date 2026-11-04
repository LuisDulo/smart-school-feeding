"""
Head-to-head comparison of the anomaly-detection models for the
Smart School Feeding Management System.

Models:   Isolation Forest (tree-ensemble, deployed) and
          Local Outlier Factor (density-based, novelty mode)
Protocol: one stratified 70/30 split of all transactions. Both models are fit
          on the same 70% (unsupervised — no labels), with the same scaler and
          the same contamination threshold, then scored on the same held-out
          30%. The synthetic `is_anomaly` label is used only to measure
          precision, recall, F1 and AUC-ROC.
Output:   models/anomaly_model_comparison.json (read by the backend and shown
          on the super admin "Model Comparison" page)
"""
import json
import os
import sys

from sklearn.ensemble import IsolationForest
from sklearn.metrics import (confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from anomaly_features import FEATURES, load_feature_frame

DEPLOYED_MODEL = 'Isolation Forest'  # the detector the backend actually uses

df = load_feature_frame()
X = df[FEATURES].values
y = df['is_anomaly'].values

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.30, random_state=42, stratify=y)

scaler = StandardScaler().fit(X_train)
X_train_s, X_test_s = scaler.transform(X_train), scaler.transform(X_test)

contamination = max(0.01, round(float(y_train.mean()) + 0.005, 4))
print(f"\nTrain rows: {len(X_train)}, test rows: {len(X_test)} "
      f"({int(y_test.sum())} known anomalies in test), contamination={contamination}")

candidates = [
    dict(name='Isolation Forest', short='IF',
         type='Tree ensemble — isolates points with random splits',
         model=IsolationForest(n_estimators=100,
                               max_samples=min(256, len(X_train)),
                               contamination=contamination, random_state=42)),
    dict(name='Local Outlier Factor', short='LOF',
         type='Density-based — compares local density with neighbours',
         model=LocalOutlierFactor(n_neighbors=min(20, len(X_train) - 1),
                                  contamination=contamination, novelty=True)),
]

results = []
for c in candidates:
    c['model'].fit(X_train_s)
    scores = c['model'].decision_function(X_test_s)
    pred = (c['model'].predict(X_test_s) == -1).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, pred, labels=[0, 1]).ravel()
    entry = {
        'name': c['name'],
        'short': c['short'],
        'type': c['type'],
        'precision': round(float(precision_score(y_test, pred, zero_division=0)), 4),
        'recall': round(float(recall_score(y_test, pred, zero_division=0)), 4),
        'f1': round(float(f1_score(y_test, pred, zero_division=0)), 4),
        'auc_roc': round(float(roc_auc_score(y_test, -scores)), 4),
        'true_positives': int(tp), 'false_positives': int(fp),
        'false_negatives': int(fn), 'true_negatives': int(tn),
        'flagged': int(pred.sum()),
        'deployed': c['name'] == DEPLOYED_MODEL,
    }
    results.append(entry)
    print(f"{entry['name']:<22} P={entry['precision']:.4f} R={entry['recall']:.4f} "
          f"F1={entry['f1']:.4f} AUC={entry['auc_roc']:.4f} "
          f"(TP={tp} FP={fp} FN={fn})")

best = max(results, key=lambda r: (r['f1'], r['auc_roc']))
print(f"\nBest anomaly model on held-out data: {best['name']} (F1={best['f1']})")

out = {
    'best_model': best['name'],
    'deployed_model': DEPLOYED_MODEL,
    'selection_metric': 'F1-score (ties broken by AUC-ROC)',
    'dataset': {
        'transactions': int(len(df)),
        'known_anomalies': int(y.sum()),
        'anomaly_rate_pct': round(float(y.mean()) * 100, 2),
        'train_rows': int(len(X_train)),
        'test_rows': int(len(X_test)),
        'test_anomalies': int(y_test.sum()),
        'features': FEATURES,
        'contamination': contamination,
    },
    'evaluation_note': ('Both models are fit without labels on the same 70% of '
                        'transactions and scored on the same held-out 30%; the '
                        'synthetic anomaly label is used only for these metrics.'),
    'caution': (f'Only {int(y_test.sum())} labelled anomalies are in the held-out '
                f'set, so a difference of a single transaction moves precision and '
                f'recall noticeably. Treat the ranking as indicative, not conclusive.'),
    'models': results,
}
os.makedirs('models', exist_ok=True)
with open('models/anomaly_model_comparison.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print("\nSaved ml/models/anomaly_model_comparison.json")
