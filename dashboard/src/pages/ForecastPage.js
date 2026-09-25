import React, { useState, useEffect } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts';
import { FiBarChart2, FiSettings } from 'react-icons/fi';
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

export default function ForecastPage() {
  const [forecasts, setForecasts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [modelInfo, setModelInfo] = useState(null);
  const [selectedModel, setSelectedModel] = useState('xgboost');
  const [selectedHorizon, setSelectedHorizon] = useState('five_day');

  useEffect(() => {
    forecastAPI.history()
      .then(res => setForecasts(res.data))
      .finally(() => setLoading(false));
    forecastAPI.models()
      .then(res => {
        if (res.data?.default_model) setSelectedModel(res.data.default_model);
      })
      .catch(() => {});
  }, []);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const res = await forecastAPI.generate(selectedModel, selectedHorizon);
      setForecasts(prev => {
        const newDates = new Set(
          res.data.forecasts.map(f => f.forecast_date));
        const filtered = prev.filter(f => !newDates.has(f.forecast_date));
        return [...filtered, ...res.data.forecasts]
          .sort((a, b) => new Date(a.forecast_date) -
                          new Date(b.forecast_date));
      });
      setModelInfo(res.data.model_info);
    } catch (e) {
      alert(e.response?.data?.error ||
        'Generation failed. Ensure Django is running and model is trained.');
    } finally {
      setGenerating(false);
    }
  };

  const chartData = forecasts.slice(-20).map(f => ({
    date: new Date(f.forecast_date).toLocaleDateString(
      'en-KE', { day: 'numeric', month: 'short' }),
    meals: f.predicted_meals,
    cost: f.predicted_cost_ksh,
  }));

  return (
    <div style={styles.page}>
      <Topbar
        title="Demand Forecast"
        subtitle="Linear Regression · Random Forest · XGBoost — scikit-learn"
      />
      <div style={styles.content}>
        <div style={styles.headerRow}>
          <p style={styles.modelBadge}>
            <FiBarChart2 style={styles.badgeIcon} />
            {MODEL_OPTIONS.find(m => m.key === selectedModel)?.label}
            {' '}· 6 features ·{' '}
            {HORIZON_OPTIONS.find(h => h.key === selectedHorizon)?.label} forecast
          </p>
          {modelInfo && (
            <p style={styles.modelDetail}>
              Enrolment: {modelInfo.enrolment} ·
              Rolling avg: {modelInfo.rolling_7day_avg} meals/day
            </p>
          )}
        </div>

        <div style={styles.card}>
          <h3 style={styles.chartTitle}>Select Model</h3>
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

          <h3 style={styles.chartTitle}>Forecast Range</h3>
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
              : `Generate ${HORIZON_OPTIONS.find(h => h.key === selectedHorizon)?.label} Forecast · ${MODEL_OPTIONS.find(m => m.key === selectedModel)?.label}`}
          </button>
        </div>

        {/* Line chart */}
        <div style={styles.chartCard}>
          <h3 style={styles.chartTitle}>Predicted Meals — Next Days</h3>
          {chartData.length === 0 ? (
            <div style={styles.empty}>
              No forecasts yet. Click Generate above.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip
                  formatter={(val, name) =>
                    name === 'meals'
                      ? [`${val} meals`, 'Predicted meals']
                      : [`KES ${val?.toLocaleString()}`, 'Estimated cost']}
                />
                <Line type="monotone" dataKey="meals"
                  stroke="#1A6E3C" strokeWidth={2}
                  dot={{ fill: '#1A6E3C', r: 4 }} name="meals" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Forecast table */}
        <div style={styles.tableCard}>
          <h3 style={styles.chartTitle}>Forecast Detail</h3>
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
              {loading ? (
                <tr><td colSpan={4} style={styles.emptyCell}>Loading...</td></tr>
              ) : forecasts.length === 0 ? (
                <tr>
                  <td colSpan={4} style={styles.emptyCell}>
                    No forecasts generated yet
                  </td>
                </tr>
              ) : forecasts.slice().reverse().map((f, i) => (
                <tr key={f.id}
                  style={i % 2 === 0 ? {} : { background: '#F9FAFB' }}>
                  <td style={styles.td}>
                    {new Date(f.forecast_date).toLocaleDateString(
                      'en-KE', { weekday: 'short',
                                 day: 'numeric', month: 'short',
                                 year: 'numeric' })}
                  </td>
                  <td style={{ ...styles.td, fontWeight: 700,
                               color: '#1A6E3C' }}>
                    {f.predicted_meals}
                  </td>
                  <td style={{ ...styles.td, fontWeight: 700,
                               color: '#1A3A5C' }}>
                    {f.predicted_cost_ksh?.toLocaleString('en-KE',
                      { minimumFractionDigits: 2 })}
                  </td>
                  <td style={{ ...styles.td, color: '#9CA3AF',
                               fontSize: 11 }}>
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
  content: { padding: 32 },
  headerRow: { marginBottom: 24 },
  modelBadge: { background: '#EEF0FB', color: '#3A4AB0', fontSize: 12,
                fontWeight: 600, padding: '8px 16px',
                borderRadius: 8, margin: 0, display: 'inline-flex',
                alignItems: 'center', gap: 8 },
  badgeIcon: { width: 15, height: 15, flexShrink: 0 },
  modelDetail: { color: '#6B7280', fontSize: 12, margin: '6px 0 0' },
  card: { background: '#fff', borderRadius: 12, padding: 24, marginBottom: 24,
          boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  selectorRow: { display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 },
  modelBtn: { border: '1px solid #E5E7EB', borderRadius: 8, padding: '8px 16px',
              fontSize: 12, fontWeight: 600, cursor: 'pointer',
              background: '#fff', color: '#374151' },
  modelBtnActive: { background: '#1A3A5C', border: '1px solid #1A3A5C', color: '#fff' },
  generateBtn: { background: '#1A6E3C', color: '#fff', border: 'none',
                 borderRadius: 10, padding: '12px 20px',
                 fontSize: 13, fontWeight: 700, cursor: 'pointer',
                 display: 'flex', alignItems: 'center', gap: 8 },
  btnIcon: { width: 15, height: 15, flexShrink: 0 },
  chartCard: { background: '#fff', borderRadius: 12, padding: 24,
               marginBottom: 24, boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  chartTitle: { margin: '0 0 16px', fontSize: 15,
                fontWeight: 700, color: '#1A3A5C' },
  empty: { textAlign: 'center', padding: 40,
           color: '#9CA3AF', fontSize: 14 },
  tableCard: { background: '#fff', borderRadius: 12, overflow: 'hidden',
               boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  table: { width: '100%', borderCollapse: 'collapse' },
  thead: { background: '#1A3A5C' },
  th: { padding: '14px 20px', textAlign: 'left',
        fontSize: 12, fontWeight: 700, color: '#fff' },
  td: { padding: '14px 20px', fontSize: 13, color: '#374151',
        borderBottom: '1px solid #F3F4F6' },
  emptyCell: { padding: 40, textAlign: 'center',
               color: '#9CA3AF', fontSize: 14 },
};
