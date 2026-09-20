import React, { useState, useEffect } from 'react';
import {
  FiSettings, FiCheckCircle, FiCalendar, FiSmartphone,
  FiCheck, FiAlertTriangle
} from 'react-icons/fi';
import Topbar from '../components/Topbar';
import api from '../services/api';

const SEVERITY_COLORS = {
  HIGH:   { bg: '#FEE2E2', color: '#C0392B', border: '#F87171' },
  MEDIUM: { bg: '#FEF3C7', color: '#D07020', border: '#FCD34D' },
  LOW:    { bg: '#F0F4F8', color: '#5A6A7A', border: '#CBD5E1' },
};

export default function AnomalyFlags() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('pending');
  const [reviewing, setReviewing] = useState(null);
  const [notes, setNotes] = useState('');
  const [running, setRunning] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const param = filter === 'all' ? '' : `?reviewed=${filter === 'pending' ? 'false' : 'true'}`;
      const res = await api.get(`/anomalies/flags/${param}`);
      setData(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filter]);

  const handleRunDetection = async () => {
    setRunning(true);
    try {
      const res = await api.post('/anomalies/run/');
      alert(`Detection complete. ${res.data.new_flags_created} new flags created.`);
      load();
    } catch (e) {
      alert('Detection failed. Ensure model is trained.');
    } finally {
      setRunning(false);
    }
  };

  const handleReview = async (flagId, action) => {
    try {
      await api.post(`/anomalies/flags/${flagId}/review/`, {
        action, review_notes: notes
      });
      setReviewing(null);
      setNotes('');
      load();
    } catch (e) {
      alert(e.response?.data?.error || 'Review failed.');
    }
  };

  return (
    <div style={styles.page}>
      <Topbar
        title="Anomaly Flag Queue"
        subtitle="Isolation Forest model · review suspicious transactions"
      />
      <div style={styles.content}>

        {/* Summary cards */}
        {data && (
          <div style={styles.summaryRow}>
            {[
              { label: 'Total flags', val: data.total, color: '#1A3A5C' },
              { label: 'Pending review', val: data.pending, color: '#C0392B' },
              { label: 'High severity', val: data.high_severity, color: '#D07020' },
            ].map(s => (
              <div key={s.label} style={{
                ...styles.summaryCard,
                borderTop: `4px solid ${s.color}`
              }}>
                <p style={{ ...styles.summaryVal, color: s.color }}>
                  {s.val}
                </p>
                <p style={styles.summaryLabel}>{s.label}</p>
              </div>
            ))}

            <div style={styles.summaryCard}>
              <button
                style={styles.runBtn}
                onClick={handleRunDetection}
                disabled={running}
              >
                <FiSettings style={styles.btnIcon} />
                {running ? 'Running...' : 'Run Detection'}
              </button>
              <p style={styles.summaryLabel}>Score all transactions</p>
            </div>
          </div>
        )}

        {/* Filter tabs */}
        <div style={styles.tabs}>
          {['pending', 'reviewed', 'all'].map(f => (
            <button
              key={f}
              style={{
                ...styles.tab,
                ...(filter === f ? styles.tabActive : {})
              }}
              onClick={() => setFilter(f)}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>

        {/* Flag cards */}
        {loading ? (
          <p style={styles.loading}>Loading flags...</p>
        ) : !data || data.flags.length === 0 ? (
          <div style={styles.empty}>
            <p><FiCheckCircle style={styles.emptyIcon} /> No flags in this view</p>
            <p style={{ fontSize: 13, color: '#9CA3AF' }}>
              {filter === 'pending'
                ? 'All anomaly flags have been reviewed.'
                : 'No flags found for this filter.'}
            </p>
          </div>
        ) : data.flags.map(flag => {
          const sc = SEVERITY_COLORS[flag.severity] || SEVERITY_COLORS.LOW;
          const isReviewing = reviewing === flag.id;

          return (
            <div key={flag.id} style={{
              ...styles.flagCard,
              borderLeft: `5px solid ${sc.border}`
            }}>
              <div style={styles.flagHeader}>
                <div style={styles.flagLeft}>
                  <span style={{
                    ...styles.severityBadge,
                    background: sc.bg,
                    color: sc.color
                  }}>
                    {flag.severity}
                  </span>
                  <span style={styles.flagStudent}>
                    {flag.transaction.student_name}
                  </span>
                  <span style={styles.flagAmount}>
                    KES {flag.transaction.amount_ksh?.toLocaleString()}
                  </span>
                </div>
                <div style={styles.flagRight}>
                  <span style={styles.flagScore}>
                    Score: {flag.anomaly_score}
                  </span>
                  <span style={styles.flagDate}>
                    {new Date(flag.flagged_at).toLocaleDateString('en-KE')}
                  </span>
                </div>
              </div>

              <div style={styles.flagDetails}>
                <span style={styles.flagDetail}>
                  <FiCalendar style={styles.detailIcon} />
                  {new Date(flag.transaction.created_at)
                    .toLocaleString('en-KE')}
                </span>
                <span style={styles.flagDetail}>
                  <FiSmartphone style={styles.detailIcon} />
                  {flag.transaction.mpesa_reference || '—'}
                </span>
                {flag.reviewed && (
                  <span style={{
                    ...styles.flagDetail, color: '#1A6E3C'
                  }}>
                    <FiCheckCircle style={styles.detailIcon} />
                    Reviewed by {flag.reviewed_by_name}
                    {flag.review_notes &&
                      ` · ${flag.review_notes}`}
                  </span>
                )}
              </div>

              {!flag.reviewed && (
                <div style={styles.flagActions}>
                  {!isReviewing ? (
                    <button
                      style={styles.reviewBtn}
                      onClick={() => setReviewing(flag.id)}
                    >
                      Review Flag
                    </button>
                  ) : (
                    <div style={styles.reviewPanel}>
                      <textarea
                        style={styles.notesInput}
                        placeholder="Add review notes (optional)..."
                        value={notes}
                        onChange={e => setNotes(e.target.value)}
                        rows={2}
                      />
                      <div style={styles.reviewBtns}>
                        <button
                          style={styles.legitimateBtn}
                          onClick={() => handleReview(
                            flag.id, 'legitimate')}
                        >
                          <FiCheck style={styles.btnIconSm} /> Mark Legitimate
                        </button>
                        <button
                          style={styles.irregularBtn}
                          onClick={() => handleReview(
                            flag.id, 'confirmed_irregular')}
                        >
                          <FiAlertTriangle style={styles.btnIconSm} /> Confirm Irregular
                        </button>
                        <button
                          style={styles.cancelBtn}
                          onClick={() => {
                            setReviewing(null);
                            setNotes('');
                          }}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

const styles = {
  page: { flex: 1, display: 'flex', flexDirection: 'column',
          background: '#F7F9FC', overflow: 'auto' },
  content: { padding: 32 },
  summaryRow: { display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gap: 16, marginBottom: 24 },
  summaryCard: { background: '#fff', borderRadius: 12,
                 padding: '16px 20px',
                 boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  summaryVal: { fontSize: 28, fontWeight: 700, margin: '0 0 4px' },
  summaryLabel: { fontSize: 12, color: '#6B7280', margin: 0 },
  runBtn: { background: '#1A3A5C', color: '#fff', border: 'none',
            borderRadius: 8, padding: '10px 16px', fontSize: 13,
            fontWeight: 600, cursor: 'pointer', width: '100%',
            marginBottom: 8, display: 'flex', alignItems: 'center',
            justifyContent: 'center', gap: 6 },
  btnIcon: { width: 14, height: 14 },
  tabs: { display: 'flex', gap: 8, marginBottom: 20 },
  tab: { border: '1px solid #E5E7EB', borderRadius: 8,
         padding: '8px 20px', fontSize: 13, fontWeight: 600,
         cursor: 'pointer', background: '#fff', color: '#374151' },
  tabActive: { background: '#1A3A5C', border: '1px solid #1A3A5C',
               color: '#fff' },
  loading: { textAlign: 'center', color: '#9CA3AF', padding: 40 },
  empty: { textAlign: 'center', padding: 60, color: '#6B7280',
           fontSize: 16 },
  emptyIcon: { width: 20, height: 20, verticalAlign: -4, marginRight: 8,
               color: '#1A6E3C' },
  flagCard: { background: '#fff', borderRadius: 12,
              padding: 20, marginBottom: 12,
              boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  flagHeader: { display: 'flex', justifyContent: 'space-between',
                alignItems: 'center', marginBottom: 10 },
  flagLeft: { display: 'flex', alignItems: 'center', gap: 12 },
  flagRight: { display: 'flex', flexDirection: 'column',
               alignItems: 'flex-end', gap: 4 },
  severityBadge: { fontSize: 11, fontWeight: 700, padding: '3px 10px',
                   borderRadius: 10 },
  flagStudent: { fontSize: 14, fontWeight: 700, color: '#1A3A5C' },
  flagAmount: { fontSize: 14, fontWeight: 700, color: '#C0392B' },
  flagScore: { fontSize: 12, color: '#6B7280' },
  flagDate: { fontSize: 11, color: '#9CA3AF' },
  flagDetails: { display: 'flex', gap: 20, flexWrap: 'wrap',
                 borderTop: '1px solid #F3F4F6', paddingTop: 10,
                 marginTop: 4 },
  flagDetail: { fontSize: 12, color: '#6B7280', display: 'flex',
                alignItems: 'center', gap: 6 },
  detailIcon: { width: 13, height: 13, flexShrink: 0 },
  flagActions: { marginTop: 12 },
  reviewBtn: { background: '#1A3A5C', color: '#fff', border: 'none',
               borderRadius: 8, padding: '8px 20px', fontSize: 13,
               fontWeight: 600, cursor: 'pointer' },
  reviewPanel: { background: '#F7F9FC', borderRadius: 8, padding: 16 },
  notesInput: { width: '100%', border: '1px solid #E5E7EB',
                borderRadius: 6, padding: '8px 12px', fontSize: 13,
                resize: 'vertical', marginBottom: 10,
                boxSizing: 'border-box' },
  reviewBtns: { display: 'flex', gap: 10 },
  btnIconSm: { width: 13, height: 13 },
  legitimateBtn: { background: '#1A6E3C', color: '#fff', border: 'none',
                   borderRadius: 8, padding: '8px 16px',
                   fontSize: 13, fontWeight: 600, cursor: 'pointer',
                   display: 'flex', alignItems: 'center', gap: 6 },
  irregularBtn: { background: '#C0392B', color: '#fff', border: 'none',
                  display: 'flex', alignItems: 'center', gap: 6,
                  borderRadius: 8, padding: '8px 16px',
                  fontSize: 13, fontWeight: 600, cursor: 'pointer' },
  cancelBtn: { background: '#fff', color: '#374151',
               border: '1px solid #E5E7EB', borderRadius: 8,
               padding: '8px 16px', fontSize: 13, cursor: 'pointer' },
};
