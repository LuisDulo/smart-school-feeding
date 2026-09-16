import React, { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer
} from 'recharts';
import { superAdminAPI } from '../../services/superadminApi';

export default function SASchoolDrillDown({ schoolId, schoolName, onBack }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    superAdminAPI.schoolDetail(schoolId)
      .then(r => setData(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [schoolId]);

  if (loading) return (
    <div style={styles.loading}>
      Loading {schoolName}...
    </div>
  );
  if (!data) return (
    <div style={styles.loading}>Failed to load school.</div>
  );

  const { school, trend_7days,
          low_balance_students, pending_flags } = data;

  return (
    <div style={styles.page}>
      <div style={styles.topbar}>
        <div>
          <button style={styles.backBtn} onClick={onBack}>
            ← Back to Network
          </button>
          <h1 style={styles.title}>{school.name}</h1>
          <p style={styles.subtitle}>
            Viewing as Super Admin · {school.county}
          </p>
        </div>
        <div style={styles.viewingBanner}>
          👁 Impersonation View
        </div>
      </div>

      <div style={styles.content}>
        {/* School stat cards */}
        <div style={styles.statsGrid}>
          {[
            { label: 'Students', val: school.student_count,
              color: '#1A3A5C' },
            { label: 'Meals Today', val: school.meals_today,
              color: '#1A6E3C' },
            { label: 'Collected Today (KES)',
              val: school.collected_today_ksh?.toLocaleString(),
              color: '#3A4AB0' },
            { label: 'Low Balance', val: school.low_balance_count,
              color: '#D07020' },
            { label: 'Active Flags', val: school.pending_flags,
              color: '#C0392B' },
            { label: 'Avg Balance (KES)',
              val: school.avg_balance_ksh?.toFixed(2),
              color: school.avg_balance_ksh < 100
                ? '#C0392B' : '#1A6E3C' },
          ].map(s => (
            <div key={s.label}
              style={{ ...styles.statCard,
                       borderTop: `4px solid ${s.color}` }}>
              <p style={{ ...styles.statVal,
                          color: s.color }}>{s.val}</p>
              <p style={styles.statLabel}>{s.label}</p>
            </div>
          ))}
        </div>

        <div style={styles.chartsRow}>
          {/* 7-day trend */}
          <div style={styles.chartCard}>
            <h3 style={styles.chartTitle}>7-Day Trend</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={trend_7days}>
                <CartesianGrid strokeDasharray="3 3"
                               stroke="#F3F4F6" />
                <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="meals" fill="#1A6E3C"
                     name="Meals served"
                     radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Pending flags */}
          <div style={styles.flagsCard}>
            <h3 style={styles.chartTitle}>
              Pending Anomaly Flags
              {pending_flags.length > 0 && (
                <span style={styles.flagCount}>
                  {pending_flags.length}
                </span>
              )}
            </h3>
            {pending_flags.length === 0 ? (
              <p style={styles.noFlags}>
                ✅ No pending flags
              </p>
            ) : pending_flags.map(f => (
              <div key={f.id} style={styles.flagItem}>
                <div>
                  <p style={styles.flagStudent}>{f.student}</p>
                  <p style={styles.flagAmount}>
                    KES {f.amount_ksh?.toLocaleString()}
                  </p>
                </div>
                <span style={{
                  ...styles.scoreBadge,
                  background: f.score >= 0.80
                    ? '#FEE2E2' : '#FEF3C7',
                  color: f.score >= 0.80
                    ? '#C0392B' : '#D07020'
                }}>
                  {f.score}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Low balance students */}
        <div style={styles.tableCard}>
          <h3 style={styles.chartTitle}>
            Low Balance Students (showing 20)
          </h3>
          <div style={{ overflowX: 'auto' }}>
          <table style={styles.table}>
            <thead>
              <tr style={styles.thead}>
                {['Student Name', 'Balance (KES)',
                  'Status'].map(h => (
                  <th key={h} style={styles.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {low_balance_students.length === 0 ? (
                <tr><td colSpan={3} style={styles.empty}>No students found.</td></tr>
              ) : low_balance_students.map((s, i) => (
                <tr key={i}
                  style={i % 2 === 0 ? {} :
                    { background: '#F9FAFB' }}>
                  <td style={styles.td}>{s.student_name}</td>
                  <td style={{
                    ...styles.td, fontWeight: 700,
                    color: s.balance_ksh < 100
                      ? '#C0392B' : '#D07020'
                  }}>
                    {s.balance_ksh?.toLocaleString('en-KE', {
                      minimumFractionDigits: 2 })}
                  </td>
                  <td style={styles.td}>
                    <span style={s.is_low
                      ? styles.badgeRed : styles.badgeGreen}>
                      {s.is_low ? '⚠️ Low' : '✓ OK'}
                    </span>
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
  topbar: { background: '#1A3A5C', padding: '16px 32px',
            display: 'flex', justifyContent: 'space-between',
            alignItems: 'center', flexWrap: 'wrap', gap: 10 },
  backBtn: { background: 'transparent', border: '1px solid #4A7A9B',
             color: '#A8D8C0', borderRadius: 6, padding: '6px 12px',
             fontSize: 12, cursor: 'pointer', marginBottom: 8,
             display: 'block' },
  title: { color: '#fff', fontSize: 20,
           fontWeight: 700, margin: 0 },
  subtitle: { color: '#6B9AB8', fontSize: 12, margin: '4px 0 0' },
  viewingBanner: { background: '#D07020', color: '#fff',
                   padding: '8px 16px', borderRadius: 8,
                   fontSize: 12, fontWeight: 700 },
  content: { padding: 32 },
  statsGrid: { display: 'grid',
               gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
               gap: 16, marginBottom: 24 },
  statCard: { background: '#fff', borderRadius: 12, padding: 16,
              boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  statVal: { fontSize: 22, fontWeight: 700, margin: '0 0 4px' },
  statLabel: { fontSize: 11, color: '#6B7280', margin: 0 },
  chartsRow: { display: 'grid',
               gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
               gap: 20, marginBottom: 24 },
  chartCard: { background: '#fff', borderRadius: 12, padding: 24,
               boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  chartTitle: { margin: '0 0 16px', fontSize: 14,
                fontWeight: 700, color: '#1A3A5C',
                display: 'flex', alignItems: 'center', gap: 10 },
  flagsCard: { background: '#fff', borderRadius: 12, padding: 24,
               boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  flagCount: { background: '#C0392B', color: '#fff',
               fontSize: 10, fontWeight: 700, borderRadius: 10,
               padding: '2px 8px' },
  noFlags: { color: '#1A6E3C', fontSize: 14, marginTop: 16 },
  flagItem: { display: 'flex', justifyContent: 'space-between',
              alignItems: 'center', padding: '10px 0',
              borderBottom: '1px solid #F3F4F6' },
  flagStudent: { margin: 0, fontSize: 13,
                 fontWeight: 700, color: '#1A3A5C' },
  flagAmount: { margin: '2px 0 0', fontSize: 12, color: '#C0392B' },
  scoreBadge: { fontSize: 12, fontWeight: 700,
                padding: '4px 10px', borderRadius: 10 },
  tableCard: { background: '#fff', borderRadius: 12,
               overflow: 'hidden',
               boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
               padding: '24px 24px 8px' },
  table: { width: '100%', borderCollapse: 'collapse', minWidth: 420 },
  thead: { background: '#1A3A5C' },
  th: { padding: '12px 16px', textAlign: 'left',
        fontSize: 11, fontWeight: 700, color: '#fff' },
  td: { padding: '12px 16px', fontSize: 13,
        color: '#374151', borderBottom: '1px solid #F3F4F6' },
  empty: { padding: 24, textAlign: 'center', color: '#9CA3AF' },
  badgeGreen: { background: '#D1FAE5', color: '#1A6E3C',
                padding: '3px 10px', borderRadius: 10,
                fontSize: 11, fontWeight: 700 },
  badgeRed: { background: '#FEE2E2', color: '#C0392B',
              padding: '3px 10px', borderRadius: 10,
              fontSize: 11, fontWeight: 700 },
};
