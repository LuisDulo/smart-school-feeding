import React, { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import {
  FiAward, FiCheckCircle, FiXCircle, FiSettings
} from 'react-icons/fi';
import Topbar from '../components/Topbar';
import { forecastAPI } from '../services/api';

const MODEL_OPTIONS = [
  { key: 'linear_regression', label: 'Linear Regression' },
  { key: 'random_forest', label: 'Random Forest' },
  { key: 'xgboost', label: 'XGBoost' },
];

const HORIZON_OPTIONS = [
  { key: 'five_day', label: '5-Day' },
  { key: 'month', label: 'Month' },
  { key: 'term', label: 'Rest of Term' },
];

export default function ModelComparison() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [selectedModel, setSelectedModel] = useState('xgboost');
  const [selectedHorizon, setSelectedHorizon] = useState('five_day');
  const [genMsg, setGenMsg] = useState('');
  const [forecasts, setForecasts] = useState([]);
  const [lastModelUsed, setLastModelUsed] = useState('');

  useEffect(() => {
    forecastAPI.models()
      .then(r => {
        setData(r.data);
        if (r.data?.default_model) setSelectedModel(r.data.default_model);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
    forecastAPI.history()
      .then(r => setForecasts(r.data))
      .catch(() => {});
  }, []);

  const handleGenerate = async () => {
    setGenerating(true);
    setGenMsg('');
    try {
      const res = await forecastAPI.generate(selectedModel, selectedHorizon);
      setGenMsg(
        `Forecast generated using ${res.data.model_used}. ` +
        `${res.data.forecasts.length} day(s) predicted.`);
      setLastModelUsed(res.data.model_used);
      setForecasts(prev => {
        const newDates = new Set(
          res.data.forecasts.map(f => f.forecast_date));
        const filtered = prev.filter(f => !newDates.has(f.forecast_date));
        return [...filtered, ...res.data.forecasts]
          .sort((a, b) => new Date(a.forecast_date) - new Date(b.forecast_date));
      });
    } catch (e) {
      setGenMsg(e.response?.data?.error || 'Generation failed. Ensure the model is trained.');
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return <div style={styles.loading}>Loading model comparison data...</div>;
  }

  const comparison = data?.comparison;
  const models = comparison?.models || [];
  const rfMetrics = data?.random_forest_metrics;
  const xgbMetrics = data?.xgboost_metrics;
  const riskMetrics = data?.risk_classifier_metrics;
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
      <Topbar
        title="ML Model Comparison"
        subtitle="Linear Regression · Random Forest · XGBoost"
      />
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

        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Generate Forecast — Select Model</h3>
          <p style={styles.cardNote}>
            Choose which model produces the demand forecast.
            {winner && ` ${winner} currently has the lowest MAE.`}
          </p>
          <div style={styles.selectorRow}>
            {MODEL_OPTIONS.map(({ key, label }) => (
              <button
                key={key}
                style={{
                  ...styles.modelBtn,
                  ...(selectedModel === key ? styles.modelBtnActive : {})
                }}
                onClick={() => setSelectedModel(key)}
              >
                {label}
              </button>
            ))}
          </div>

          <p style={styles.cardNote}>Choose the forecast range.</p>
          <div style={styles.selectorRow}>
            {HORIZON_OPTIONS.map(({ key, label }) => (
              <button
                key={key}
                style={{
                  ...styles.modelBtn,
                  ...(selectedHorizon === key ? styles.modelBtnActive : {})
                }}
                onClick={() => setSelectedHorizon(key)}
              >
                {label}
              </button>
            ))}
          </div>

          <button
            style={{ ...styles.generateBtn, ...(generating ? { opacity: 0.6 } : {}) }}
            onClick={handleGenerate}
            disabled={generating}
          >
            <FiSettings style={styles.btnIcon} />
            {generating
              ? 'Generating...'
              : `Generate ${HORIZON_OPTIONS.find(h => h.key === selectedHorizon)?.label} · ${selectedModel.replace(/_/g, ' ')}`}
          </button>
          {genMsg && (
            <p style={{
              marginTop: 12, fontSize: 13,
              color: genMsg.startsWith('Forecast') ? '#1A6E3C' : '#C0392B'
            }}>
              {genMsg}
            </p>
          )}
        </div>

        <div style={styles.tableCard}>
          <h3 style={{ ...styles.chartTitle, padding: '20px 24px 0' }}>
            Forecast Detail{lastModelUsed && ` — ${lastModelUsed}`}
          </h3>
          <table style={styles.table}>
            <thead>
              <tr style={styles.thead}>
                {['Forecast Date', 'Predicted Meals',
                  'Estimated Cost (KES)', 'Generated At'].map(h => (
                  <th key={h} style={styles.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {forecasts.length === 0 ? (
                <tr>
                  <td colSpan={4} style={styles.emptyCell}>
                    No forecasts generated yet. Pick a model above and click Generate.
                  </td>
                </tr>
              ) : forecasts.slice().reverse().map((f, i) => (
                <tr key={f.id} style={i % 2 === 0 ? {} : { background: '#F9FAFB' }}>
                  <td style={styles.td}>
                    {new Date(f.forecast_date).toLocaleDateString(
                      'en-KE', { weekday: 'short', day: 'numeric',
                                 month: 'short', year: 'numeric' })}
                  </td>
                  <td style={{ ...styles.td, fontWeight: 700, color: '#1A6E3C' }}>
                    {f.predicted_meals}
                  </td>
                  <td style={{ ...styles.td, fontWeight: 700, color: '#1A3A5C' }}>
                    {f.predicted_cost_ksh?.toLocaleString('en-KE',
                      { minimumFractionDigits: 2 })}
                  </td>
                  <td style={{ ...styles.td, color: '#9CA3AF', fontSize: 11 }}>
                    {new Date(f.generated_at).toLocaleString('en-KE')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

const styles = {
  page: { flex: 1, display: 'flex', flexDirection: 'column',
          background: '#F7F9FC', overflow: 'auto' },
  loading: { display: 'flex', alignItems: 'center', justifyContent: 'center',
             height: '100vh', color: '#6B7280' },
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
