import React, { useState, useEffect } from 'react';
import { FiCpu, FiAlertCircle, FiCheckCircle } from 'react-icons/fi';
import Topbar from '../components/Topbar';
import { forecastAPI } from '../services/api';

export default function BalanceRisk() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    forecastAPI.risk()
      .then(r => setData(r.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div style={styles.page}>
      <Topbar
        title="Balance Depletion Risk"
        subtitle="Random Forest Classifier — students predicted to run out within 7 days"
      />
      <div style={styles.content}>
        {loading ? (
          <p style={{ color: '#9CA3AF' }}>Running risk classifier...</p>
        ) : error || !data ? (
          <p style={{ color: '#C0392B' }}>
            Risk classifier not loaded. Run train_balance_risk_classifier.py first.
          </p>
        ) : (
          <>
            <div style={styles.summaryRow}>
              <div style={{ ...styles.summaryCard, borderTop: '4px solid #C0392B' }}>
                <p style={{ ...styles.summaryVal, color: '#C0392B' }}>
                  {data.at_risk_count}
                </p>
                <p style={styles.summaryLabel}>Students at risk</p>
              </div>
              <div style={{ ...styles.summaryCard, borderTop: '4px solid #1A6E3C' }}>
                <p style={{ ...styles.summaryVal, color: '#1A6E3C' }}>
                  {data.safe_count}
                </p>
                <p style={styles.summaryLabel}>Safe students</p>
              </div>
              <div style={{ ...styles.summaryCard, borderTop: '4px solid #3A4AB0' }}>
                <p style={{ ...styles.summaryVal, color: '#3A4AB0' }}>
                  {data.total_students}
                </p>
                <p style={styles.summaryLabel}>Total enrolled</p>
              </div>
              <div style={styles.modelBox}>
                <p style={styles.modelTitle}>
                  <FiCpu style={styles.modelIcon} /> Model
                </p>
                <p style={styles.modelName}>{data.model}</p>
                <p style={styles.modelDesc}>Binary classification · 7 features</p>
              </div>
            </div>

            <div style={styles.tableCard}>
              <h3 style={styles.tableTitle}>
                <FiAlertCircle style={styles.titleIcon} />
                At-Risk Students
                <span style={styles.atRiskBadge}>{data.at_risk_count} students</span>
              </h3>
              <p style={styles.tableNote}>
                {data.message}. Consider sending top-up reminders to their parents.
              </p>

              {data.at_risk_students.length === 0 ? (
                <p style={{ color: '#1A6E3C', padding: 24, display: 'flex',
                            alignItems: 'center', gap: 8 }}>
                  <FiCheckCircle /> No students at risk this week.
                </p>
              ) : (
                <table style={styles.table}>
                  <thead>
                    <tr style={styles.thead}>
                      {['Student Name', 'Balance (KES)', 'Meals/Week (avg)',
                        'Est. Days Remaining', 'Days Since Top-Up',
                        'Risk Probability'].map(h => (
                        <th key={h} style={styles.th}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.at_risk_students.map((s, i) => (
                      <tr key={s.student_id} style={{
                        ...(i % 2 === 0 ? {} : { background: '#FFF7ED' }),
                        borderLeft: '4px solid #C0392B'
                      }}>
                        <td style={{ ...styles.td, fontWeight: 700, color: '#1A3A5C' }}>
                          {s.student_name}
                        </td>
                        <td style={{ ...styles.td, fontWeight: 700, color: '#C0392B' }}>
                          {s.balance_ksh?.toLocaleString('en-KE', { minimumFractionDigits: 2 })}
                        </td>
                        <td style={styles.td}>{s.avg_meals_per_week}</td>
                        <td style={{ ...styles.td, fontWeight: 700,
                          color: s.estimated_days_remaining < 3 ? '#C0392B' : '#D07020' }}>
                          {s.estimated_days_remaining > 90 ? '90+' : s.estimated_days_remaining}
                        </td>
                        <td style={styles.td}>{s.days_since_last_topup} days</td>
                        <td style={styles.td}>
                          <div style={styles.probBar}>
                            <div style={{
                              ...styles.probFill,
                              width: `${s.risk_probability * 100}%`,
                              background: s.risk_probability > 0.8 ? '#C0392B'
                                : s.risk_probability > 0.6 ? '#D07020' : '#1A6E3C'
                            }} />
                          </div>
                          <span style={{ fontSize: 11, color: '#6B7280' }}>
                            {(s.risk_probability * 100).toFixed(1)}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

const styles = {
  page: { flex: 1, display: 'flex', flexDirection: 'column',
          background: '#F7F9FC', overflow: 'auto' },
  content: { padding: 32 },
  summaryRow: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
                gap: 16, marginBottom: 24 },
  summaryCard: { background: '#fff', borderRadius: 12, padding: '16px 20px',
                 boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  summaryVal: { fontSize: 32, fontWeight: 700, margin: '0 0 4px' },
  summaryLabel: { fontSize: 12, color: '#6B7280', margin: 0 },
  modelBox: { background: '#EEF0FB', borderRadius: 12, padding: '16px 20px',
              borderTop: '4px solid #3A4AB0' },
  modelTitle: { margin: '0 0 4px', fontSize: 11, color: '#3A4AB0',
                fontWeight: 700, display: 'flex', alignItems: 'center', gap: 6 },
  modelIcon: { width: 13, height: 13, flexShrink: 0 },
  modelName: { margin: '0 0 4px', fontSize: 14, fontWeight: 700, color: '#1A3A5C' },
  modelDesc: { margin: 0, fontSize: 11, color: '#6B7280' },
  tableCard: { background: '#fff', borderRadius: 12, overflow: 'hidden',
               boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  tableTitle: { margin: 0, fontSize: 15, fontWeight: 700, color: '#1A3A5C',
                padding: '20px 24px 0', display: 'flex', alignItems: 'center', gap: 10 },
  titleIcon: { width: 16, height: 16, flexShrink: 0, color: '#C0392B' },
  atRiskBadge: { background: '#FEE2E2', color: '#C0392B', fontSize: 11,
                 fontWeight: 700, padding: '3px 10px', borderRadius: 10 },
  tableNote: { margin: '8px 0 16px', fontSize: 12, color: '#6B7280', padding: '0 24px' },
  table: { width: '100%', borderCollapse: 'collapse' },
  thead: { background: '#1A3A5C' },
  th: { padding: '12px 16px', textAlign: 'left', fontSize: 11,
        fontWeight: 700, color: '#fff' },
  td: { padding: '12px 16px', fontSize: 13, color: '#374151',
        borderBottom: '1px solid #F3F4F6' },
  probBar: { height: 6, background: '#F3F4F6', borderRadius: 3,
             marginBottom: 4, overflow: 'hidden' },
  probFill: { height: '100%', borderRadius: 3 },
};
