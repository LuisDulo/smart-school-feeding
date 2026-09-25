import React, { useState, useEffect } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, BarChart, Bar, Legend
} from 'recharts';
import { FiDollarSign, FiAlertCircle, FiAlertTriangle, FiSettings } from 'react-icons/fi';
import { MdOutlineRestaurant } from 'react-icons/md';
import Topbar from '../components/Topbar';
import StatCard from '../components/StatCard';
import { forecastAPI } from '../services/api';
import { latestForecastBatch } from '../utils/forecastUtils';

const HORIZON_OPTIONS = [
  { key: 'five_day', label: '5-Day' },
  { key: 'month', label: 'Month' },
];

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [forecasts, setForecasts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [horizon, setHorizon] = useState('five_day');

  useEffect(() => {
    loadStats();
    loadForecasts();
  }, []);

  const loadStats = async () => {
    try {
      const res = await forecastAPI.stats();
      setStats(res.data);
    } catch (e) {
      console.error('Stats error:', e.message);
    } finally {
      setLoading(false);
    }
  };

  const loadForecasts = async () => {
    try {
      // /forecast/history/ returns every forecast ever generated for
      // this school — only show the most recent single Generate batch,
      // or this widget mixes forecasts from unrelated runs.
      const res = await forecastAPI.history();
      setForecasts(latestForecastBatch(res.data));
    } catch (e) {
      console.error('Forecast history error:', e.message);
    }
  };

  const handleGenerateForecast = async () => {
    setGenerating(true);
    try {
      const res = await forecastAPI.generate(undefined, horizon);
      setForecasts(res.data.forecasts);
      alert(`Forecast generated for ${res.data.forecasts.length} days.`);
    } catch (e) {
      alert(e.response?.data?.error ||
        'Forecast generation failed. Check that the model is trained.');
    } finally {
      setGenerating(false);
    }
  };

  const trendData = stats?.meal_trend_7days || [];

  return (
    <div style={styles.page}>
      <Topbar
        title="Dashboard"
        subtitle={`${new Date().toLocaleDateString('en-KE', {
          weekday: 'long', day: 'numeric',
          month: 'long', year: 'numeric'
        })}`}
      />

      <div style={styles.content}>
        {/* Stat Cards */}
        <div style={styles.statsRow}>
          <StatCard icon={MdOutlineRestaurant} label="Meals served today"
            value={stats?.meals_today ?? '—'}
            color="#1A6E3C" loading={loading} />
          <StatCard icon={FiDollarSign} label="Collected today (KES)"
            value={stats?.collected_today_ksh?.toLocaleString() ?? '—'}
            color="#3A4AB0" loading={loading} />
          <StatCard icon={FiAlertCircle} label="Low balance students"
            value={stats?.low_balance_count ?? '—'}
            color="#D07020" loading={loading} />
          <StatCard icon={FiAlertTriangle} label="Anomaly flags pending"
            value={stats?.pending_anomaly_flags ?? '—'}
            color="#C0392B" loading={loading} />
        </div>

        <div style={styles.chartsRow}>
          {/* Meal trend chart */}
          <div style={styles.chartCard}>
            <h3 style={styles.chartTitle}>
              Meal Collection — Last 7 Days
            </h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
                <XAxis dataKey="day" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="meals" fill="#1A6E3C"
                     name="Meals served" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Forecast panel */}
          <div style={styles.forecastCard}>
            <div style={styles.forecastHeader}>
              <h3 style={styles.chartTitle}>Demand Forecast</h3>
              <div style={styles.forecastHeaderActions}>
                <select
                  style={styles.horizonSelect}
                  value={horizon}
                  onChange={e => setHorizon(e.target.value)}
                  disabled={generating}
                >
                  {HORIZON_OPTIONS.map(h => (
                    <option key={h.key} value={h.key}>{h.label}</option>
                  ))}
                </select>
                <button
                  style={styles.generateBtn}
                  onClick={handleGenerateForecast}
                  disabled={generating}
                >
                  <FiSettings style={styles.btnIcon} />
                  {generating ? 'Generating...' : 'Generate'}
                </button>
              </div>
            </div>

            {forecasts.length === 0 ? (
              <div style={styles.emptyForecast}>
                <p>No forecasts yet.</p>
                <p style={{ fontSize: 12, color: '#9CA3AF' }}>
                  Click Generate to run the Linear Regression model.
                </p>
              </div>
            ) : (
              <div>
                {forecasts.slice(0, 5).map(f => (
                  <div key={f.id} style={styles.forecastRow}>
                    <div>
                      <p style={styles.forecastDate}>
                        {new Date(f.forecast_date).toLocaleDateString(
                          'en-KE', { weekday: 'short',
                                     day: 'numeric', month: 'short' })}
                      </p>
                    </div>
                    <div style={styles.forecastRight}>
                      <span style={styles.forecastMeals}>
                        {f.predicted_meals} meals
                      </span>
                      <span style={styles.forecastCost}>
                        KES {f.predicted_cost_ksh?.toLocaleString()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

const styles = {
  page: { flex: 1, display: 'flex', flexDirection: 'column',
          background: '#F7F9FC', overflow: 'auto' },
  content: { padding: 32 },
  statsRow: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
              gap: 20, marginBottom: 24 },
  chartsRow: { display: 'grid', gridTemplateColumns: '1.6fr 1fr',
               gap: 20 },
  chartCard: { background: '#fff', borderRadius: 12, padding: 24,
               boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  chartTitle: { margin: '0 0 16px', fontSize: 15,
                fontWeight: 700, color: '#1A3A5C' },
  forecastCard: { background: '#fff', borderRadius: 12, padding: 24,
                  boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  forecastHeader: { display: 'flex', justifyContent: 'space-between',
                    alignItems: 'center', marginBottom: 16 },
  forecastHeaderActions: { display: 'flex', alignItems: 'center', gap: 8 },
  horizonSelect: { border: '1px solid #E5E7EB', borderRadius: 8,
                   padding: '7px 8px', fontSize: 12, fontWeight: 600,
                   color: '#374151', background: '#fff', cursor: 'pointer' },
  generateBtn: { background: '#1A6E3C', color: '#fff', border: 'none',
                 borderRadius: 8, padding: '8px 14px', fontSize: 12,
                 fontWeight: 600, cursor: 'pointer', display: 'flex',
                 alignItems: 'center', gap: 6 },
  btnIcon: { width: 14, height: 14 },
  emptyForecast: { textAlign: 'center', padding: '32px 0',
                   color: '#6B7280', fontSize: 14 },
  forecastRow: { display: 'flex', justifyContent: 'space-between',
                 alignItems: 'center', padding: '10px 0',
                 borderBottom: '1px solid #F3F4F6' },
  forecastDate: { margin: 0, fontSize: 13,
                  fontWeight: 600, color: '#1A3A5C' },
  forecastRight: { display: 'flex', flexDirection: 'column',
                   alignItems: 'flex-end' },
  forecastMeals: { fontSize: 14, fontWeight: 700, color: '#1A6E3C' },
  forecastCost: { fontSize: 11, color: '#6B7280', marginTop: 2 },
};
