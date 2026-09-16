import React, { useState, useEffect } from 'react';
import {
  LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { superAdminAPI } from '../../services/superadminApi';

const SCHOOL_COLORS = ['#1A6E3C', '#3A4AB0', '#C0392B',
                        '#D07020', '#9673a6'];

export default function SAOverview({ onDrillDown }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    superAdminAPI.overview()
      .then(r => setData(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={styles.loading}>Loading network overview...</div>;
  if (!data) return <div style={styles.loading}>Failed to load data.</div>;

  const { summary, school_performance,
          meal_trend_14days, activity_feed,
          school_names } = data;

  // Prepare trend chart data
  const trendChartData = meal_trend_14days.map(d => {
    const entry = { day: d.day };
    school_names.forEach(name => {
      entry[name] = d.schools[name] || 0;
    });
    return entry;
  });

  return (
    <div style={styles.page}>
      {/* Header */}
      <div style={styles.topbar}>
        <div>
          <h1 style={styles.title}>Network Overview</h1>
          <p style={styles.subtitle}>
            Webmasters Kenya — All Schools Dashboard
          </p>
        </div>
        <div style={styles.liveBadge}>&#128994; Live</div>
      </div>

      <div style={styles.content}>
        {/* Summary cards */}
        <div style={styles.statsGrid}>
          {[
            { icon: '🏫', label: 'Total Schools',
              val: summary.total_schools, color: '#1A3A5C' },
            { icon: '👥', label: 'Total Students',
              val: summary.total_students, color: '#1A6E3C' },
            { icon: '🍽️', label: 'Meals Today',
              val: summary.meals_today, color: '#3A4AB0' },
            { icon: '💰', label: 'Collected Today (KES)',
              val: summary.collected_today_ksh?.toLocaleString(),
              color: '#1A6E3C' },
            { icon: '⚠️', label: 'Low Balance Students',
              val: summary.low_balance_total, color: '#D07020' },
            { icon: '🚨', label: 'Active Anomaly Flags',
              val: summary.active_flags, color: '#C0392B' },
          ].map(s => (
            <div key={s.label}
              style={{ ...styles.statCard,
                       borderTop: `4px solid ${s.color}` }}>
              <div style={styles.statRow}>
                <span style={styles.statIcon}>{s.icon}</span>
                <span style={{ ...styles.statVal, color: s.color }}>
                  {s.val}
                </span>
              </div>
              <p style={styles.statLabel}>{s.label}</p>
            </div>
          ))}
        </div>

        <div style={styles.chartsRow}>
          {/* 14-day trend multi-line chart */}
          <div style={styles.chartCard}>
            <h3 style={styles.chartTitle}>
              Meals Served — Last 14 Days (All Schools)
            </h3>
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={trendChartData}>
                <CartesianGrid strokeDasharray="3 3"
                               stroke="#F3F4F6" />
                <XAxis dataKey="day"
                       tick={{ fontSize: 10 }}
                       interval={1} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                {school_names.map((name, i) => (
                  <Line key={name} type="monotone"
                    dataKey={name}
                    stroke={SCHOOL_COLORS[i % SCHOOL_COLORS.length]}
                    strokeWidth={2}
                    dot={{ r: 3 }} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Activity feed */}
          <div style={styles.feedCard}>
            <h3 style={styles.chartTitle}>Recent Activity</h3>
            <div style={styles.feedList}>
              {activity_feed.slice(0, 10).map((a, i) => (
                <div key={i} style={styles.feedItem}>
                  <span style={styles.feedIcon}>
                    {a.type === 'meal' ? '🍽️' : '💳'}
                  </span>
                  <div style={styles.feedText}>
                    <p style={styles.feedSchool}>{a.school}</p>
                    <p style={styles.feedDesc}>{a.description}</p>
                  </div>
                  <span style={styles.feedTime}>
                    {new Date(a.timestamp).toLocaleTimeString(
                      'en-KE', { hour: '2-digit',
                                  minute: '2-digit' })}
                  </span>
                </div>
              ))}
              {activity_feed.length === 0 && (
                <p style={{ color: '#9CA3AF', fontSize: 13 }}>
                  No recent activity.
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Per-school performance table */}
        <div style={styles.tableCard}>
          <h3 style={styles.chartTitle}>
            Today's School Performance
          </h3>
          <div style={{ overflowX: 'auto' }}>
          <table style={styles.table}>
            <thead>
              <tr style={styles.thead}>
                {['School', 'Students', 'Meals Today',
                  'Attendance', 'Collected (KES)',
                  'Flags', 'Action'].map(h => (
                  <th key={h} style={styles.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {school_performance.map((s, i) => (
                <tr key={s.id}
                  style={{
                    ...(i % 2 === 0 ? {} : { background: '#F9FAFB' }),
                    ...(s.below_target
                      ? { borderLeft: '4px solid #FCD34D' } : {})
                  }}>
                  <td style={{ ...styles.td, fontWeight: 700,
                               color: '#1A3A5C' }}>
                    {s.name}
                  </td>
                  <td style={styles.td}>{s.students}</td>
                  <td style={styles.td}>{s.meals_today}</td>
                  <td style={{
                    ...styles.td, fontWeight: 700,
                    color: s.attendance_pct >= 80
                      ? '#1A6E3C' : '#D07020'
                  }}>
                    {s.attendance_pct}%
                  </td>
                  <td style={styles.td}>
                    {s.collected_ksh?.toLocaleString()}
                  </td>
                  <td style={{
                    ...styles.td,
                    color: s.pending_flags > 0
                      ? '#C0392B' : '#1A6E3C',
                    fontWeight: 700
                  }}>
                    {s.pending_flags > 0
                      ? `⚠️ ${s.pending_flags}` : '✓ 0'}
                  </td>
                  <td style={styles.td}>
                    <button
                      style={styles.drillBtn}
                      onClick={() => onDrillDown(s.id, s.name)}
                    >
                      View →
                    </button>
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
             color: '#6B7280', fontSize: 16 },
  topbar: { background: '#1A3A5C', padding: '20px 32px',
            display: 'flex', justifyContent: 'space-between',
            alignItems: 'center', flexWrap: 'wrap', gap: 10 },
  title: { color: '#fff', fontSize: 22,
           fontWeight: 700, margin: 0 },
  subtitle: { color: '#6B9AB8', fontSize: 13, margin: '4px 0 0' },
  liveBadge: { background: '#1A6E3C', color: '#fff',
               padding: '6px 14px', borderRadius: 20,
               fontSize: 12, fontWeight: 700 },
  content: { padding: 32 },
  statsGrid: { display: 'grid',
               gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
               gap: 16, marginBottom: 24 },
  statCard: { background: '#fff', borderRadius: 12,
              padding: '16px 20px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  statRow: { display: 'flex', justifyContent: 'space-between',
             alignItems: 'center', marginBottom: 6 },
  statIcon: { fontSize: 20 },
  statVal: { fontSize: 24, fontWeight: 700 },
  statLabel: { fontSize: 11, color: '#6B7280', margin: 0 },
  chartsRow: { display: 'grid',
               gridTemplateColumns: 'minmax(0, 1.6fr) minmax(0, 1fr)',
               gap: 20, marginBottom: 24 },
  chartCard: { background: '#fff', borderRadius: 12,
               padding: 24,
               boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  chartTitle: { margin: '0 0 16px', fontSize: 14,
                fontWeight: 700, color: '#1A3A5C' },
  feedCard: { background: '#fff', borderRadius: 12,
              padding: 24,
              boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
              overflow: 'hidden' },
  feedList: { overflowY: 'auto', maxHeight: 260 },
  feedItem: { display: 'flex', alignItems: 'flex-start',
              gap: 10, padding: '8px 0',
              borderBottom: '1px solid #F3F4F6' },
  feedIcon: { fontSize: 16, marginTop: 2 },
  feedText: { flex: 1 },
  feedSchool: { margin: 0, fontSize: 11,
                fontWeight: 700, color: '#1A3A5C' },
  feedDesc: { margin: '2px 0 0', fontSize: 12, color: '#6B7280' },
  feedTime: { fontSize: 11, color: '#9CA3AF', whiteSpace: 'nowrap' },
  tableCard: { background: '#fff', borderRadius: 12,
               overflow: 'hidden',
               boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
               padding: '24px 24px 8px' },
  table: { width: '100%', borderCollapse: 'collapse',
           minWidth: 640 },
  thead: { background: '#1A3A5C' },
  th: { padding: '12px 16px', textAlign: 'left',
        fontSize: 11, fontWeight: 700, color: '#fff' },
  td: { padding: '12px 16px', fontSize: 13,
        color: '#374151', borderBottom: '1px solid #F3F4F6' },
  drillBtn: { background: '#1A3A5C', color: '#fff',
              border: 'none', borderRadius: 6,
              padding: '6px 12px', fontSize: 11,
              fontWeight: 700, cursor: 'pointer' },
};
