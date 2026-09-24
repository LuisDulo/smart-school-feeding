import React, { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, PieChart, Pie, Cell
} from 'recharts';
import { FiCheck } from 'react-icons/fi';
import { superAdminAPI } from '../../services/superadminApi';

const COLORS = ['#1A6E3C','#3A4AB0','#C0392B','#D07020','#9673a6'];

export default function SAAnalytics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    superAdminAPI.analytics()
      .then(r => setData(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div style={styles.loading}>Loading analytics...</div>);
  if (!data) return (
    <div style={styles.loading}>No data available.</div>);

  const { weekly_collections_per_school,
          balance_distribution,
          forecast_accuracy } = data;

  // Recharts' Pie mis-renders when most brackets are zero (a real school
  // rarely has students in every KES bracket) — drop empty ones rather
  // than fight the renderer, which also declutters the legend.
  const nonEmptyBalanceBrackets = balance_distribution.filter(b => b.count > 0);

  // Flatten weekly collections for grouped bar chart
  const weeklyData = ['W-4','W-3','W-2','W-1'].map(week => {
    const entry = { week };
    weekly_collections_per_school.forEach(school => {
      const w = school.weekly.find(w => w.week === week);
      entry[school.school] = w ? w.collected_ksh : 0;
    });
    return entry;
  });

  const schoolNames = weekly_collections_per_school
    .map(s => s.school);

  return (
    <div style={styles.page}>
      <div style={styles.topbar}>
        <h1 style={styles.title}>Cross-School Analytics</h1>
        <p style={styles.subtitle}>
          Comparative performance across all schools
        </p>
      </div>

      <div style={styles.content}>
        <div style={styles.chartsRow}>
          {/* Weekly collections per school */}
          <div style={styles.chartCard}>
            <h3 style={styles.chartTitle}>
              Weekly Collections per School (KES)
            </h3>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={weeklyData}>
                <CartesianGrid strokeDasharray="3 3"
                               stroke="#F3F4F6" />
                <XAxis dataKey="week" />
                <YAxis />
                <Tooltip
                  formatter={v =>
                    `KES ${v?.toLocaleString()}`} />
                <Legend />
                {schoolNames.map((name, i) => (
                  <Bar key={name} dataKey={name}
                    fill={COLORS[i % COLORS.length]}
                    radius={[4, 4, 0, 0]} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Balance distribution pie */}
          <div style={styles.chartCard}>
            <h3 style={styles.chartTitle}>
              Student Balance Distribution (All Schools)
            </h3>
            {nonEmptyBalanceBrackets.length === 0 ? (
              <p style={{ color: '#9CA3AF', fontSize: 13 }}>No balance data yet.</p>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={nonEmptyBalanceBrackets}
                    dataKey="count"
                    nameKey="bracket"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label={({ bracket, count }) =>
                      `${bracket}: ${count}`}
                  >
                    {nonEmptyBalanceBrackets.map((_, i) => (
                      <Cell key={i}
                        fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Forecast accuracy table */}
        <div style={styles.tableCard}>
          <h3 style={styles.chartTitle}>
            Demand Forecast Accuracy per School
          </h3>
          <p style={styles.tableNote}>
            MAE = Mean Absolute Error (meals/day).
            Target: MAE &lt; 15.
          </p>
          <div style={{ overflowX: 'auto' }}>
          <table style={styles.table}>
            <thead>
              <tr style={styles.thead}>
                {['School', 'Avg MAE (meals/day)',
                  'Forecasts Evaluated', 'Status'].map(h => (
                  <th key={h} style={styles.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {forecast_accuracy.map((f, i) => (
                <tr key={f.school}
                  style={i % 2 === 0 ? {} :
                    { background: '#F9FAFB' }}>
                  <td style={{ ...styles.td, fontWeight: 700,
                               color: '#1A3A5C' }}>
                    {f.school}
                  </td>
                  <td style={{
                    ...styles.td, fontWeight: 700,
                    color: f.avg_mae === null ? '#9CA3AF' :
                      f.avg_mae < 15 ? '#1A6E3C' : '#C0392B'
                  }}>
                    {f.avg_mae !== null
                      ? f.avg_mae : 'No data yet'}
                  </td>
                  <td style={styles.td}>
                    {f.forecasts_evaluated}
                  </td>
                  <td style={styles.td}>
                    {f.avg_mae === null
                      ? <span style={styles.badgeGray}>No forecasts</span>
                      : f.avg_mae < 15
                      ? <span style={styles.badgeGreen}><FiCheck style={styles.badgeIcon} /> On target</span>
                      : <span style={styles.badgeRed}>Above target</span>
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
      </div>
    </div>
  );
}

const styles = {
  page: { flex: 1, display: 'flex', flexDirection: 'column',
          background: '#F7F9FC', overflow: 'auto' },
  loading: { display: 'flex', alignItems: 'center',
             justifyContent: 'center', height: '100vh',
             color: '#6B7280' },
  topbar: { background: '#1A3A5C', padding: '20px 32px' },
  title: { color: '#fff', fontSize: 22,
           fontWeight: 700, margin: 0 },
  subtitle: { color: '#6B9AB8', fontSize: 13, margin: '4px 0 0' },
  content: { padding: 32 },
  chartsRow: { display: 'grid',
               gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
               gap: 20, marginBottom: 24 },
  chartCard: { background: '#fff', borderRadius: 12, padding: 24,
               boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  chartTitle: { margin: '0 0 16px', fontSize: 14,
                fontWeight: 700, color: '#1A3A5C' },
  tableCard: { background: '#fff', borderRadius: 12,
               overflow: 'hidden', padding: 24,
               boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  tableNote: { fontSize: 12, color: '#6B7280', margin: '0 0 16px' },
  table: { width: '100%', borderCollapse: 'collapse',
           minWidth: 560 },
  thead: { background: '#1A3A5C' },
  th: { padding: '12px 16px', textAlign: 'left',
        fontSize: 11, fontWeight: 700, color: '#fff' },
  td: { padding: '12px 16px', fontSize: 13,
        color: '#374151', borderBottom: '1px solid #F3F4F6' },
  badgeGreen: { background: '#D1FAE5', color: '#1A6E3C',
                padding: '3px 10px', borderRadius: 10,
                fontSize: 11, fontWeight: 700,
                display: 'inline-flex', alignItems: 'center', gap: 4 },
  badgeRed: { background: '#FEE2E2', color: '#C0392B',
              padding: '3px 10px', borderRadius: 10,
              fontSize: 11, fontWeight: 700 },
  badgeGray: { background: '#F3F4F6', color: '#6B7280',
               padding: '3px 10px', borderRadius: 10,
               fontSize: 11, fontWeight: 700 },
  badgeIcon: { width: 11, height: 11 },
};
