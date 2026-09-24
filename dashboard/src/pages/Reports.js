import React, { useState, useEffect } from 'react';
import { FiDollarSign, FiAlertTriangle, FiDownload } from 'react-icons/fi';
import { MdOutlineRestaurant } from 'react-icons/md';
import Topbar from '../components/Topbar';
import api from '../services/api';

export default function Reports() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/reports/summary/')
      .then(res => setSummary(res.data))
      .catch(e => console.error(e))
      .finally(() => setLoading(false));
  }, []);

  const downloadCSV = async (endpoint, filename) => {
    try {
      const res = await api.get(endpoint, {
        responseType: 'blob' });
      const url = window.URL.createObjectURL(
        new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (e) {
      alert('Download failed. Please try again.');
    }
  };

  const reports = [
    {
      Icon: FiDollarSign,
      title: 'Payment Collection Report',
      desc: 'All M-Pesa transactions with status and anomaly flag indicator.',
      endpoint: '/reports/payments/csv/?days=90',
      filename: `payments_${new Date().toISOString().split('T')[0]}.csv`,
      color: '#1A6E3C',
      bg: '#D1FAE5'
    },
    {
      Icon: MdOutlineRestaurant,
      title: 'Meal Distribution Report',
      desc: 'Daily meal events, student names, and balance after deduction.',
      endpoint: '/reports/meals/csv/?days=90',
      filename: `distribution_${new Date().toISOString().split('T')[0]}.csv`,
      color: '#3A4AB0',
      bg: '#EEF0FB'
    },
    {
      Icon: FiAlertTriangle,
      title: 'Anomaly Detection Report',
      desc: 'All flagged transactions with scores, severity, and review outcomes.',
      endpoint: '/reports/anomalies/csv/',
      filename: `anomaly_flags_${new Date().toISOString().split('T')[0]}.csv`,
      color: '#C0392B',
      bg: '#FEE2E2'
    },
  ];

  return (
    <div style={styles.page}>
      <Topbar
        title="Reports & Analytics"
        subtitle="Download CSV reports and view term summary"
      />
      <div style={styles.content}>

        {/* Term summary stats */}
        {summary && (
          <div style={styles.summaryCard}>
            <h3 style={styles.sectionTitle}>
              Term Summary — Last 90 Days
            </h3>
            <div style={styles.statsGrid}>
              {[
                { label: 'Students enrolled',
                  val: summary.students?.total_enrolled },
                { label: 'Total collected (KES)',
                  val: summary.payments
                    ?.total_collected_ksh?.toLocaleString() },
                { label: 'Total transactions',
                  val: summary.payments?.total_transactions },
                { label: 'Total meals served',
                  val: summary.meals?.total_meals_served },
                { label: 'Avg meals per day',
                  val: summary.meals?.average_per_day },
                { label: 'Anomaly flags total',
                  val: summary.anomalies?.total_flagged },
                { label: 'Pending review',
                  val: summary.anomalies?.pending_review },
                { label: 'Low balance students',
                  val: summary.students?.low_balance },
              ].map(s => (
                <div key={s.label} style={styles.statItem}>
                  <p style={styles.statVal}>{s.val ?? '—'}</p>
                  <p style={styles.statLabel}>{s.label}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Report download cards */}
        <h3 style={styles.sectionTitle}>Download Reports</h3>
        <div style={styles.reportGrid}>
          {reports.map(r => (
            <div key={r.title} style={{
              ...styles.reportCard,
              borderTop: `4px solid ${r.color}`
            }}>
              <div style={{
                ...styles.reportIcon,
                background: r.bg, color: r.color
              }}>
                <r.Icon size={22} />
              </div>
              <h4 style={styles.reportTitle}>{r.title}</h4>
              <p style={styles.reportDesc}>{r.desc}</p>
              <button
                style={{
                  ...styles.downloadBtn,
                  background: r.color
                }}
                onClick={() =>
                  downloadCSV(r.endpoint, r.filename)}
              >
                <FiDownload style={styles.downloadIcon} /> Download CSV
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
  content: { padding: 32 },
  sectionTitle: { fontSize: 16, fontWeight: 700,
                  color: '#1A3A5C', margin: '0 0 16px' },
  summaryCard: { background: '#fff', borderRadius: 12,
                 padding: 24, marginBottom: 32,
                 boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  statsGrid: { display: 'grid',
               gridTemplateColumns: 'repeat(4, 1fr)',
               gap: 20, marginTop: 16 },
  statItem: { textAlign: 'center', padding: '12px 0',
              borderRight: '1px solid #F3F4F6' },
  statVal: { fontSize: 22, fontWeight: 700,
             color: '#1A3A5C', margin: '0 0 4px' },
  statLabel: { fontSize: 11, color: '#6B7280', margin: 0 },
  reportGrid: { display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: 20 },
  reportCard: { background: '#fff', borderRadius: 12,
                padding: 24,
                boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  reportIcon: { width: 48, height: 48, borderRadius: 12,
                display: 'flex', alignItems: 'center',
                justifyContent: 'center', fontSize: 24,
                marginBottom: 16 },
  reportTitle: { fontSize: 15, fontWeight: 700,
                 color: '#1A3A5C', margin: '0 0 8px' },
  reportDesc: { fontSize: 13, color: '#6B7280',
                margin: '0 0 20px', lineHeight: 1.5 },
  downloadBtn: { color: '#fff', border: 'none',
                 borderRadius: 8, padding: '10px 20px',
                 fontSize: 13, fontWeight: 600,
                 cursor: 'pointer', width: '100%', display: 'flex',
                 alignItems: 'center', justifyContent: 'center', gap: 8 },
  downloadIcon: { width: 14, height: 14 },
};
