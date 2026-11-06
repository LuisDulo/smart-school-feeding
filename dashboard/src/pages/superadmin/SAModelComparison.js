import React, { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import {
  FiAward, FiCheckCircle, FiXCircle
} from 'react-icons/fi';
import { forecastAPI } from '../../services/api';

export default function SAModelComparison() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    forecastAPI.models()
      .then(r => setData(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div style={styles.loading}>Loading model comparison data...</div>;
  }

  const comparison = data?.comparison;
  const models = comparison?.models || [];
  const rfMetrics = data?.random_forest_metrics;
  const xgbMetrics = data?.xgboost_metrics;
  const riskMetrics = data?.risk_classifier_metrics;
  const anomaly = data?.anomaly_comparison;
  const anomalyModels = anomaly?.models || [];
  const mealAnomaly = data?.meal_anomaly_evaluation;
  const bestAnomalyF1 = anomalyModels.length
    ? Math.max(...anomalyModels.map(m => m.f1)) : null;
  const anomalyChart = ['precision', 'recall', 'f1', 'auc_roc'].map(metric => ({
    metric: { precision: 'Precision', recall: 'Recall', f1: 'F1-score', auc_roc: 'AUC-ROC' }[metric],
    ...Object.fromEntries(anomalyModels.map(m => [m.name, m[metric]])),
  }));
  const ANOMALY_COLORS = ['#1A6E3C', '#3A4AB0'];
  const winner = comparison?.best_model;

  const barData = models.map(m => ({
    name: m.name === 'Linear Regression' ? 'Linear Reg.' : m.name,
    MAE: m.mae,
    RMSE: m.rmse,
  }));

  const minMae = models.length ? Math.min(...models.map(m => m.mae)) : null;
  const minRmse = models.length ? Math.min(...models.map(m => m.rmse)) : null;
  const maxR2 = models.length ? Math.max(...models.map(m => m.r2)) : null;

  const featureBar = (title, importances, color) => !importances ? null : (
    <div style={styles.chartCard}>
      <h3 style={styles.chartTitle}>{title}</h3>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart
          layout="vertical"
          data={Object.entries(importances)
            .sort((a, b) => b[1] - a[1])
            .map(([k, v]) => ({ feature: k.replace(/_/g, ' '), value: v }))}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
          <XAxis type="number" tick={{ fontSize: 10 }} />
          <YAxis dataKey="feature" type="category" width={150}
                 tick={{ fontSize: 10 }} />
          <Tooltip />
          <Bar dataKey="value" fill={color} radius={[0, 4, 4, 0]}
               name="Importance" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );

  return (
    <div style={styles.page}>
      <div style={styles.topbar}>
        <h1 style={styles.title}>ML Model Comparison</h1>
        <p style={styles.subtitle}>
          Forecasting models, anomaly-detection models and the balance-risk
          classifier, each evaluated on the same data.
        </p>
      </div>
      <div style={styles.content}>
        <div style={styles.headerRow}>
          <div style={styles.statusRow}>
            {Object.entries(data?.models_loaded || {}).map(([key, loaded]) => (
              <div key={key} style={{
                ...styles.statusChip,
                background: loaded ? '#D1FAE5' : '#FEE2E2',
                color: loaded ? '#1A6E3C' : '#C0392B'
              }}>
                {loaded ? <FiCheckCircle style={styles.chipIcon} />
                        : <FiXCircle style={styles.chipIcon} />}
                {key.replace(/_/g, ' ')}
              </div>
            ))}
          </div>
          {winner && (
            <div style={styles.winnerBadge}>
              <FiAward style={styles.winnerIcon} /> Best Model: {winner}
            </div>
          )}
        </div>

        {models.length > 0 && (
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>
              Forecasting Model Evaluation — Test Set Results
            </h3>
            <p style={styles.cardNote}>
              Evaluated on the same held-out 20% chronological test set.
              All models trained on identical features and data.
            </p>
            <table style={styles.table}>
              <thead>
                <tr style={styles.thead}>
                  {['Model', 'Algorithm Type', 'MAE', 'RMSE', 'R²',
                    'MAPE', 'CV MAE'].map(h => (
                    <th key={h} style={styles.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {models.map((m, i) => {
                  const isWinner = m.name === winner;
                  const cvData = m.name === 'Random Forest' ? rfMetrics
                    : m.name === 'XGBoost' ? xgbMetrics : null;
                  return (
                    <tr key={m.name} style={{
                      ...(i % 2 === 0 ? {} : { background: '#F9FAFB' }),
                      ...(isWinner
                        ? { outline: '2px solid #1A6E3C', outlineOffset: -2 }
                        : {})
                    }}>
                      <td style={{ ...styles.td, fontWeight: 700, color: '#1A3A5C' }}>
                        {isWinner && <FiAward style={styles.inlineTrophy} />}
                        {m.name}
                      </td>
                      <td style={{ ...styles.td, fontSize: 11, color: '#6B7280' }}>
                        {m.type}
                      </td>
                      <td style={{ ...styles.td, fontWeight: 700,
                        color: m.mae === minMae ? '#1A6E3C' : '#374151' }}>
                        {m.mae}
                      </td>
                      <td style={{ ...styles.td, fontWeight: 700,
                        color: m.rmse === minRmse ? '#1A6E3C' : '#374151' }}>
                        {m.rmse}
                      </td>
                      <td style={{ ...styles.td, fontWeight: 700,
                        color: m.r2 === maxR2 ? '#1A6E3C' : '#374151' }}>
                        {m.r2}
                      </td>
                      <td style={styles.td}>{m.mape}%</td>
                      <td style={{ ...styles.td, color: '#6B7280' }}>
                        {cvData ? `${cvData.cv_mae_mean} ± ${cvData.cv_mae_std}` : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {comparison?.improvements && (
              <div style={styles.improvementsRow}>
                <div style={styles.improvementChip}>
                  Random Forest vs baseline MAE:{' '}
                  <strong>{comparison.improvements.rf_vs_lr_mae_pct}%</strong>
                </div>
                <div style={{ ...styles.improvementChip, background: '#EEF0FB', color: '#3A4AB0' }}>
                  XGBoost vs baseline MAE:{' '}
                  <strong>{comparison.improvements.xgb_vs_lr_mae_pct}%</strong>
                </div>
              </div>
            )}
          </div>
        )}

        <div style={styles.chartsRow}>
          <div style={styles.chartCard}>
            <h3 style={styles.chartTitle}>MAE and RMSE by Model (lower is better)</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={barData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="MAE" fill="#1A6E3C" radius={[4, 4, 0, 0]} />
                <Bar dataKey="RMSE" fill="#3A4AB0" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          {featureBar('Feature Importance — XGBoost',
            xgbMetrics?.feature_importances, '#3A4AB0')}
        </div>

        {featureBar('Feature Importance — Random Forest',
          rfMetrics?.feature_importances, '#1A6E3C')}

        {anomalyModels.length > 0 && (
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>
              Anomaly Detection Model Evaluation — Held-out Test Results
              {anomaly?.best_model && (
                <span style={styles.classifierBadge}>
                  Best on this data: {anomaly.best_model}
                </span>
              )}
            </h3>
            <p style={styles.cardNote}>
              {anomaly?.evaluation_note}{' '}
              {anomaly?.deployed_model &&
                `The deployed detector is currently ${anomaly.deployed_model}.`}
            </p>
            <table style={styles.table}>
              <thead>
                <tr style={styles.thead}>
                  {['Model', 'Approach', 'Precision', 'Recall', 'F1-score',
                    'AUC-ROC', 'Caught / Missed / False alarms', 'Status'].map(h => (
                    <th key={h} style={styles.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {anomalyModels.map((m, i) => {
                  const isBest = m.f1 === bestAnomalyF1;
                  return (
                    <tr key={m.name} style={{
                      ...(i % 2 === 0 ? {} : { background: '#F9FAFB' }),
                      ...(isBest ? { outline: '2px solid #1A6E3C', outlineOffset: -2 } : {})
                    }}>
                      <td style={{ ...styles.td, fontWeight: 700, color: '#1A3A5C' }}>
                        {isBest && <FiAward style={styles.inlineTrophy} />}
                        {m.name}
                      </td>
                      <td style={{ ...styles.td, fontSize: 11, color: '#6B7280' }}>{m.type}</td>
                      <td style={styles.td}>{m.precision}</td>
                      <td style={styles.td}>{m.recall}</td>
                      <td style={{ ...styles.td, fontWeight: 700,
                        color: isBest ? '#1A6E3C' : '#374151' }}>{m.f1}</td>
                      <td style={styles.td}>{m.auc_roc}</td>
                      <td style={{ ...styles.td, color: '#6B7280' }}>
                        {m.true_positives} / {m.false_negatives} / {m.false_positives}
                      </td>
                      <td style={styles.td}>
                        {m.deployed
                          ? <span style={styles.deployedBadge}>Deployed</span>
                          : <span style={styles.candidateBadge}>Candidate</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            <div style={{ marginTop: 20 }}>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={anomalyChart}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
                  <XAxis dataKey="metric" tick={{ fontSize: 12 }} />
                  <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend />
                  {anomalyModels.map((m, i) => (
                    <Bar key={m.name} dataKey={m.name}
                         fill={ANOMALY_COLORS[i % ANOMALY_COLORS.length]}
                         radius={[4, 4, 0, 0]} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>

            {anomaly?.dataset && (
              <p style={{ ...styles.cardNote, marginTop: 12, marginBottom: 0 }}>
                Dataset: {anomaly.dataset.transactions} transactions,{' '}
                {anomaly.dataset.known_anomalies} known anomalies
                ({anomaly.dataset.anomaly_rate_pct}%); held-out set of{' '}
                {anomaly.dataset.test_rows} transactions containing{' '}
                {anomaly.dataset.test_anomalies} anomalies. {anomaly.caution}
              </p>
            )}
          </div>
        )}

        {mealAnomaly && (
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>
              Meal-Serving Anomaly Detector
              <span style={styles.classifierBadge}>
                Isolation Forest + rules
              </span>
            </h3>
            <p style={styles.cardNote}>
              Scores every served meal on cost, hour, weekday, meals that day and
              how far the cost is from the student's usual, and applies explainable
              rules (outside serving hours, non-school days, a meal far costlier than
              usual). Repeated attempts to serve past the daily limit are flagged too.
            </p>
            <table style={styles.table}>
              <thead>
                <tr style={styles.thead}>
                  {['Detector', 'Precision', 'Recall', 'F1', 'Night', 'Weekend', 'Costly meal', 'Normal meals flagged'].map(h => (
                    <th key={h} style={styles.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  ['Model alone', mealAnomaly.metrics?.model_alone],
                  ['Model + rules (deployed)', mealAnomaly.metrics?.model_plus_rules],
                ].map(([label, m], i) => m && (
                  <tr key={label} style={{ background: i % 2 === 0 ? '#fff' : '#F9FAFB' }}>
                    <td style={{ ...styles.td, fontWeight: 600 }}>{label}</td>
                    <td style={styles.td}>{m.precision}</td>
                    <td style={styles.td}>{m.recall}</td>
                    <td style={styles.td}>{m.f1}</td>
                    <td style={styles.td}>{m.recall_by_type?.night}</td>
                    <td style={styles.td}>{m.recall_by_type?.weekend}</td>
                    <td style={styles.td}>{m.recall_by_type?.cost}</td>
                    <td style={styles.td}>{m.real_meals_flagged_pct}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p style={{ ...styles.cardNote, marginTop: 12, marginBottom: 0 }}>
              Evaluated on {mealAnomaly.dataset?.held_out_meals} held-out real meals plus{' '}
              {mealAnomaly.dataset?.injected_anomalies} injected anomalies.{' '}
              {mealAnomaly.caution}
            </p>
          </div>
        )}

        {riskMetrics && (
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>
              Balance Depletion Risk Classifier
              <span style={styles.classifierBadge}>
                Random Forest — Binary Classification
              </span>
            </h3>
            <p style={styles.cardNote}>
              Predicts which students will run out of meal balance within
              7 days, enabling proactive parent top-up reminders.
            </p>
            <div style={styles.classifierGrid}>
              {[
                { label: 'Accuracy', val: riskMetrics.accuracy, note: 'Overall correct predictions' },
                { label: 'Precision', val: riskMetrics.precision, note: 'Of flagged students, truly at risk' },
                { label: 'Recall', val: riskMetrics.recall, note: 'Of at-risk students, how many caught' },
                { label: 'F1-Score', val: riskMetrics.f1_score, note: 'Harmonic mean of precision & recall' },
                { label: 'AUC-ROC', val: riskMetrics.auc_roc, note: 'Discriminative ability (0.5–1.0)' },
                { label: 'CV F1', val: riskMetrics.cv_f1_mean, note: `± ${riskMetrics.cv_f1_std} (5-fold)` },
              ].map(s => (
                <div key={s.label} style={styles.metricBox}>
                  <p style={styles.metricVal}>{s.val ?? '—'}</p>
                  <p style={styles.metricLabel}>{s.label}</p>
                  <p style={styles.metricNote}>{s.note}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  page: { flex: 1, display: 'flex', flexDirection: 'column',
          background: '#F7F9FC', overflow: 'auto' },
  loading: { display: 'flex', alignItems: 'center', justifyContent: 'center',
             height: '100vh', color: '#6B7280' },
  topbar: { background: '#1A3A5C', padding: '20px 32px' },
  title: { color: '#fff', fontSize: 22, fontWeight: 700, margin: 0 },
  subtitle: { color: '#6B9AB8', fontSize: 13, margin: '4px 0 0' },
  content: { padding: 32 },
  headerRow: { display: 'flex', justifyContent: 'space-between',
               alignItems: 'center', marginBottom: 24, flexWrap: 'wrap', gap: 12 },
  statusRow: { display: 'flex', gap: 10, flexWrap: 'wrap' },
  statusChip: { padding: '6px 14px', borderRadius: 20, fontSize: 12,
                fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 },
  chipIcon: { width: 13, height: 13, flexShrink: 0 },
  winnerBadge: { background: '#D07020', color: '#fff', padding: '8px 16px',
                 borderRadius: 20, fontSize: 13, fontWeight: 700,
                 display: 'flex', alignItems: 'center', gap: 8 },
  winnerIcon: { width: 15, height: 15, flexShrink: 0 },
  inlineTrophy: { width: 13, height: 13, marginRight: 6, verticalAlign: -2, color: '#D07020' },
  card: { background: '#fff', borderRadius: 12, padding: 24, marginBottom: 24,
          boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  cardTitle: { margin: '0 0 6px', fontSize: 15, fontWeight: 700,
               color: '#1A3A5C', display: 'flex', alignItems: 'center', gap: 12 },
  cardNote: { margin: '0 0 16px', fontSize: 12, color: '#6B7280' },
  table: { width: '100%', borderCollapse: 'collapse' },
  thead: { background: '#1A3A5C' },
  th: { padding: '12px 14px', textAlign: 'left', fontSize: 11,
        fontWeight: 700, color: '#fff' },
  td: { padding: '12px 14px', fontSize: 13, color: '#374151',
        borderBottom: '1px solid #F3F4F6' },
  tableCard: { background: '#fff', borderRadius: 12, overflow: 'hidden',
               boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  emptyCell: { padding: 40, textAlign: 'center', color: '#9CA3AF', fontSize: 14 },
  improvementsRow: { display: 'flex', gap: 12, marginTop: 16, flexWrap: 'wrap' },
  improvementChip: { background: '#D1FAE5', color: '#1A6E3C',
                     padding: '10px 16px', borderRadius: 8, fontSize: 13 },
  chartsRow: { display: 'grid', gridTemplateColumns: '1fr 1fr',
               gap: 20, marginBottom: 24 },
  chartCard: { background: '#fff', borderRadius: 12, padding: 24,
               boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  chartTitle: { margin: '0 0 16px', fontSize: 14, fontWeight: 700, color: '#1A3A5C' },
  deployedBadge: { background: '#D1FAE5', color: '#1A6E3C', fontSize: 11,
                   fontWeight: 700, padding: '3px 10px', borderRadius: 12 },
  candidateBadge: { background: '#F3F4F6', color: '#6B7280', fontSize: 11,
                    fontWeight: 700, padding: '3px 10px', borderRadius: 12 },
  classifierBadge: { background: '#EEF0FB', color: '#3A4AB0', fontSize: 11,
                     fontWeight: 600, padding: '4px 12px', borderRadius: 20 },
  classifierGrid: { display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)',
                    gap: 16, marginTop: 16 },
  metricBox: { textAlign: 'center', padding: '16px 8px',
               background: '#F7F9FC', borderRadius: 10 },
  metricVal: { margin: 0, fontSize: 22, fontWeight: 700, color: '#1A3A5C' },
  metricLabel: { margin: '4px 0 2px', fontSize: 12, fontWeight: 700, color: '#374151' },
  metricNote: { margin: 0, fontSize: 10, color: '#9CA3AF' },
  selectorRow: { display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap' },
  modelBtn: { border: '1px solid #E5E7EB', borderRadius: 8, padding: '10px 20px',
              fontSize: 13, fontWeight: 600, cursor: 'pointer',
              background: '#fff', color: '#374151' },
  modelBtnActive: { background: '#1A3A5C', border: '1px solid #1A3A5C', color: '#fff' },
  generateBtn: { background: '#1A6E3C', color: '#fff', border: 'none',
                 borderRadius: 8, padding: '12px 24px', fontSize: 14,
                 fontWeight: 700, cursor: 'pointer', display: 'flex',
                 alignItems: 'center', gap: 8 },
  btnIcon: { width: 15, height: 15, flexShrink: 0 },
};
