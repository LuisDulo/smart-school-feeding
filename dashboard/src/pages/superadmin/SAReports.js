import React, { useState, useEffect } from 'react';
import { FiDollarSign, FiDownload } from 'react-icons/fi';
import { MdOutlineRestaurant } from 'react-icons/md';
import { superAdminAPI } from '../../services/superadminApi';

export default function SAReports() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    superAdminAPI.reportSummary()
      .then(r => setSummary(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const downloadCSV = async (type) => {
    setError('');
    try {
      const res = await superAdminAPI.reportCSV(type);
      const url = window.URL.createObjectURL(
        new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download',
        `network_${type}_${new Date()
          .toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      setError('Download failed.');
    }
  };

  return (
    <div style={styles.page}>
      <div style={styles.topbar}>
        <h1 style={styles.title}>Network Reports</h1>
        <p style={styles.subtitle}>
          Cross-school data exports and summaries
        </p>
      </div>

      <div style={styles.content}>
        {error && <div style={styles.errorBanner}>{error}</div>}

        {/* Network summary table */}
        {loading ? (
          <p style={{ color: '#9CA3AF' }}>Loading summary...</p>
        ) : summary && (
          <div style={styles.card}>
            <h3 style={styles.cardTitle}>
              Network Summary — Last {summary.period_days} Days
            </h3>
            <div style={{ overflowX: 'auto' }}>
            <table style={styles.table}>
              <thead>
                <tr style={styles.thead}>
                  {['School', 'County', 'Students',
                    'Total Collected (KES)',
                    'Meals Served', 'Anomaly Flags'].map(h => (
                    <th key={h} style={styles.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {summary.network_summary.map((s, i) => (
                  <tr key={s.school}
                    style={i % 2 === 0 ? {} :
                      { background: '#F9FAFB' }}>
                    <td style={{ ...styles.td,
                                 fontWeight: 700,
                                 color: '#1A3A5C' }}>
                      {s.school}
                    </td>
                    <td style={styles.td}>{s.county}</td>
                    <td style={styles.td}>{s.students}</td>
                    <td style={{ ...styles.td,
                                 fontWeight: 700,
                                 color: '#1A6E3C' }}>
                      {s.total_collected_ksh?.toLocaleString(
                        'en-KE', { minimumFractionDigits: 2 })}
                    </td>
                    <td style={styles.td}>{s.total_meals_served}</td>
                    <td style={{
                      ...styles.td,
                      color: s.anomaly_flags > 0
                        ? '#C0392B' : '#1A6E3C',
                      fontWeight: 700
                    }}>
                      {s.anomaly_flags}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </div>
        )}

        {/* Download buttons */}
        <div style={styles.downloadsGrid}>
          {[
            { type: 'payments', Icon: FiDollarSign,
              title: 'Network Payment Report',
              desc: 'All M-Pesa transactions across all schools with school column.',
              color: '#1A6E3C', bg: '#D1FAE5' },
            { type: 'meals', Icon: MdOutlineRestaurant,
              title: 'Network Meal Distribution',
              desc: 'All meal events across all schools — total children fed.',
              color: '#3A4AB0', bg: '#EEF0FB' },
          ].map(r => (
            <div key={r.type} style={{
              ...styles.downloadCard,
              borderTop: `4px solid ${r.color}`
            }}>
              <div style={{
                ...styles.dlIcon, background: r.bg,
                color: r.color
              }}>
                <r.Icon style={styles.dlIconSvg} />
              </div>
              <h4 style={styles.dlTitle}>{r.title}</h4>
              <p style={styles.dlDesc}>{r.desc}</p>
              <button
                style={{
                  ...styles.dlBtn, background: r.color
                }}
                onClick={() => downloadCSV(r.type)}
              >
                <FiDownload style={styles.btnIcon} /> Download CSV
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

const styles = {
  page: { flex: 1, display: 'flex', flexDirection: 'column',
          background: '#F7F9FC', overflow: 'auto' },
  topbar: { background: '#1A3A5C', padding: '20px 32px' },
  title: { color: '#fff', fontSize: 22,
           fontWeight: 700, margin: 0 },
  subtitle: { color: '#6B9AB8', fontSize: 13, margin: '4px 0 0' },
  content: { padding: 32 },
  errorBanner: { background: '#FEE2E2', color: '#C0392B',
                 padding: '10px 16px', borderRadius: 8,
                 fontSize: 13, marginBottom: 16 },
  card: { background: '#fff', borderRadius: 12, padding: 24,
          marginBottom: 24,
          boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
          overflow: 'hidden' },
  cardTitle: { margin: '0 0 16px', fontSize: 15,
               fontWeight: 700, color: '#1A3A5C' },
  table: { width: '100%', borderCollapse: 'collapse',
           minWidth: 640 },
  thead: { background: '#1A3A5C' },
  th: { padding: '12px 16px', textAlign: 'left',
        fontSize: 11, fontWeight: 700, color: '#fff' },
  td: { padding: '12px 16px', fontSize: 13,
        color: '#374151', borderBottom: '1px solid #F3F4F6' },
  downloadsGrid: { display: 'grid',
                   gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                   gap: 20 },
  downloadCard: { background: '#fff', borderRadius: 12,
                  padding: 24,
                  boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  dlIcon: { width: 48, height: 48, borderRadius: 12,
            display: 'flex', alignItems: 'center',
            justifyContent: 'center',
            marginBottom: 16 },
  dlIconSvg: { width: 24, height: 24 },
  dlTitle: { margin: '0 0 8px', fontSize: 15,
             fontWeight: 700, color: '#1A3A5C' },
  dlDesc: { margin: '0 0 20px', fontSize: 13,
            color: '#6B7280', lineHeight: 1.5 },
  dlBtn: { width: '100%', color: '#fff', border: 'none',
           borderRadius: 8, padding: '12px', fontSize: 14,
           fontWeight: 700, cursor: 'pointer',
           display: 'flex', alignItems: 'center',
           justifyContent: 'center', gap: 8 },
  btnIcon: { width: 14, height: 14 },
};
