import React, { useState, useEffect } from 'react';
import { superAdminAPI } from '../../services/superadminApi';

export default function SAAnomalies() {
  const [schools, setSchools] = useState([]);
  const [data, setData] = useState({ total: 0, pending: 0, high_severity: 0, flags: [] });
  const [loading, setLoading] = useState(true);
  const [schoolId, setSchoolId] = useState('');
  const [severity, setSeverity] = useState('');
  const [reviewed, setReviewed] = useState('false');

  useEffect(() => {
    superAdminAPI.schools().then(r => setSchools(r.data.schools)).catch(() => {});
  }, []);

  const load = () => {
    setLoading(true);
    const params = {};
    if (schoolId) params.school_id = schoolId;
    if (severity) params.severity = severity;
    if (reviewed) params.reviewed = reviewed;
    superAdminAPI.anomalies(params)
      .then(r => setData(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(load, [schoolId, severity, reviewed]);

  return (
    <div style={styles.page}>
      <div style={styles.topbar}>
        <h1 style={styles.title}>Anomaly Flags</h1>
        <p style={styles.subtitle}>Suspicious transactions across the network</p>
      </div>

      <div style={styles.content}>
        <div style={styles.statsRow}>
          <div style={styles.statCard}>
            <p style={styles.statVal}>{data.total}</p>
            <p style={styles.statLabel}>Total Flags</p>
          </div>
          <div style={{ ...styles.statCard, borderTop: '4px solid #D07020' }}>
            <p style={{ ...styles.statVal, color: '#D07020' }}>{data.pending}</p>
            <p style={styles.statLabel}>Pending Review</p>
          </div>
          <div style={{ ...styles.statCard, borderTop: '4px solid #C0392B' }}>
            <p style={{ ...styles.statVal, color: '#C0392B' }}>{data.high_severity}</p>
            <p style={styles.statLabel}>High Severity</p>
          </div>
        </div>

        <div style={styles.filters}>
          <select style={styles.select} value={schoolId} onChange={e => setSchoolId(e.target.value)}>
            <option value="">All Schools</option>
            {schools.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          <select style={styles.select} value={severity} onChange={e => setSeverity(e.target.value)}>
            <option value="">Any Severity</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
          <select style={styles.select} value={reviewed} onChange={e => setReviewed(e.target.value)}>
            <option value="false">Unreviewed</option>
            <option value="true">Reviewed</option>
            <option value="">All</option>
          </select>
        </div>

        <div style={styles.tableCard}>
          <div style={{ overflowX: 'auto' }}>
            <table style={styles.table}>
              <thead>
                <tr style={styles.thead}>
                  {['School', 'Student', 'Amount (KES)', 'M-Pesa Ref', 'Score', 'Severity', 'Status'].map(h => (
                    <th key={h} style={styles.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={7} style={styles.empty}>Loading...</td></tr>
                ) : data.flags.length === 0 ? (
                  <tr><td colSpan={7} style={styles.empty}>No flags match.</td></tr>
                ) : data.flags.map((f, i) => (
                  <tr key={f.id} style={i % 2 === 0 ? {} : { background: '#F9FAFB' }}>
                    <td style={{ ...styles.td, fontWeight: 700, color: '#1A3A5C' }}>{f.school}</td>
                    <td style={styles.td}>{f.student}</td>
                    <td style={{ ...styles.td, fontWeight: 700 }}>
                      {f.amount_ksh?.toLocaleString('en-KE', { minimumFractionDigits: 2 })}
                    </td>
                    <td style={styles.td}>{f.mpesa_ref || '—'}</td>
                    <td style={styles.td}>{f.anomaly_score}</td>
                    <td style={styles.td}>
                      <span style={
                        f.severity === 'HIGH' ? styles.badgeRed
                        : f.severity === 'MEDIUM' ? styles.badgeAmber
                        : styles.badgeGray
                      }>
                        {f.severity}
                      </span>
                    </td>
                    <td style={styles.td}>
                      {f.reviewed ? (
                        <span style={styles.badgeGreen}>Reviewed{f.reviewed_by ? ` by ${f.reviewed_by}` : ''}</span>
                      ) : (
                        <span style={styles.badgeAmber}>Pending</span>
                      )}
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
  page: { flex: 1, display: 'flex', flexDirection: 'column', background: '#F7F9FC', overflow: 'auto' },
  topbar: { background: '#1A3A5C', padding: '20px 32px' },
  title: { color: '#fff', fontSize: 22, fontWeight: 700, margin: 0 },
  subtitle: { color: '#6B9AB8', fontSize: 13, margin: '4px 0 0' },
  content: { padding: 32 },
  statsRow: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
              gap: 16, marginBottom: 20 },
  statCard: { background: '#fff', borderRadius: 12, padding: 16,
              boxShadow: '0 2px 8px rgba(0,0,0,0.04)', borderTop: '4px solid #1A3A5C' },
  statVal: { fontSize: 24, fontWeight: 700, margin: '0 0 4px', color: '#1A3A5C' },
  statLabel: { fontSize: 11, color: '#6B7280', margin: 0 },
  filters: { display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' },
  select: { border: '1px solid #E5E7EB', borderRadius: 8, padding: '10px 14px',
            fontSize: 13, background: '#fff', outline: 'none' },
  tableCard: { background: '#fff', borderRadius: 12, overflow: 'hidden',
               boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  table: { width: '100%', borderCollapse: 'collapse', minWidth: 760 },
  thead: { background: '#1A3A5C' },
  th: { padding: '12px 16px', textAlign: 'left', fontSize: 11, fontWeight: 700, color: '#fff' },
  td: { padding: '12px 16px', fontSize: 13, color: '#374151', borderBottom: '1px solid #F3F4F6' },
  empty: { padding: 40, textAlign: 'center', color: '#9CA3AF' },
  badgeGreen: { background: '#D1FAE5', color: '#1A6E3C', padding: '3px 10px', borderRadius: 10, fontSize: 11, fontWeight: 700 },
  badgeAmber: { background: '#FEF3C7', color: '#D07020', padding: '3px 10px', borderRadius: 10, fontSize: 11, fontWeight: 700 },
  badgeRed: { background: '#FEE2E2', color: '#C0392B', padding: '3px 10px', borderRadius: 10, fontSize: 11, fontWeight: 700 },
  badgeGray: { background: '#F3F4F6', color: '#6B7280', padding: '3px 10px', borderRadius: 10, fontSize: 11, fontWeight: 700 },
};
