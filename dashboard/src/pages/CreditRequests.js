import React, { useState, useEffect } from 'react';
import { FiCheck, FiX } from 'react-icons/fi';
import Topbar from '../components/Topbar';
import { paymentsAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';

const FILTERS = [
  { key: '', label: 'All' },
  { key: 'pending', label: 'Pending' },
  { key: 'approved', label: 'Approved' },
  { key: 'rejected', label: 'Rejected' },
];

export default function CreditRequests() {
  const { user } = useAuth();
  const canReview = user?.role === 'admin';
  const [filter, setFilter] = useState('pending');
  const [requests, setRequests] = useState([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reviewingId, setReviewingId] = useState(null);

  const load = () => {
    setLoading(true);
    paymentsAPI.creditRequestQueue(filter)
      .then(res => {
        setRequests(res.data.requests);
        setPendingCount(res.data.pending);
      })
      .catch(() => setError('Could not load credit requests.'))
      .finally(() => setLoading(false));
  };

  useEffect(load, [filter]);

  const handleReview = async (req, action) => {
    const verb = action === 'approved' ? 'approve' : 'reject';
    if (!window.confirm(
      action === 'approved'
        ? `Approve KES ${req.requested_amount_ksh.toFixed(2)} credit for ${req.student_name}? This raises their spending limit — it does not add real balance.`
        : `Reject this credit request from ${req.requested_by_name}?`
    )) return;

    setReviewingId(req.id);
    setError('');
    try {
      await paymentsAPI.reviewCreditRequest(req.id, { action, review_notes: '' });
      load();
    } catch (e) {
      setError(e.response?.data?.error || `Could not ${verb} request.`);
    } finally {
      setReviewingId(null);
    }
  };

  return (
    <div style={styles.page}>
      <Topbar
        title="Credit Requests"
        subtitle={canReview
          ? "Parents applying to raise their child's spending limit — approving does not add real balance"
          : "Parents applying to raise their child's spending limit (view only — only a school admin can approve or reject)"}
      />
      <div style={styles.content}>
        <div style={styles.tabs}>
          {FILTERS.map(f => (
            <div
              key={f.key}
              style={{ ...styles.tab, ...(filter === f.key ? styles.tabActive : {}) }}
              onClick={() => setFilter(f.key)}
            >
              {f.label}{f.key === 'pending' && pendingCount > 0 ? ` (${pendingCount})` : ''}
            </div>
          ))}
        </div>

        {error && <div style={styles.errorBanner}>{error}</div>}

        <div style={styles.tableWrap}>
          <table style={styles.table}>
            <thead>
              <tr style={styles.thead}>
                {['Student', 'Requested By', 'Amount (KES)', 'Reason', 'Status', ''].map(h => (
                  <th key={h} style={styles.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} style={styles.empty}>Loading...</td></tr>
              ) : requests.length === 0 ? (
                <tr><td colSpan={6} style={styles.empty}>No requests here.</td></tr>
              ) : requests.map((r, i) => (
                <tr key={r.id} style={i % 2 === 0 ? styles.trEven : styles.trOdd}>
                  <td style={{ ...styles.td, fontWeight: 600 }}>{r.student_name}</td>
                  <td style={styles.td}>{r.requested_by_name}</td>
                  <td style={{ ...styles.td, fontWeight: 700, color: '#1A3A5C' }}>
                    {r.requested_amount_ksh.toFixed(2)}
                  </td>
                  <td style={{ ...styles.td, maxWidth: 220 }}>{r.reason || '—'}</td>
                  <td style={styles.td}>
                    <span style={
                      r.status === 'pending' ? styles.badgePending
                      : r.status === 'approved' ? styles.badgeOk
                      : styles.badgeRejected
                    }>
                      {r.status}
                    </span>
                  </td>
                  <td style={styles.td}>
                    {r.status === 'pending' && (
                      canReview ? (
                        <div style={{ display: 'flex', gap: 6 }}>
                          <button
                            style={styles.approveBtn}
                            disabled={reviewingId === r.id}
                            onClick={() => handleReview(r, 'approved')}
                          >
                            <FiCheck style={styles.btnIcon} /> Approve
                          </button>
                          <button
                            style={styles.rejectBtn}
                            disabled={reviewingId === r.id}
                            onClick={() => handleReview(r, 'rejected')}
                          >
                            <FiX style={styles.btnIcon} /> Reject
                          </button>
                        </div>
                      ) : (
                        <span style={styles.viewOnlyNote}>Awaiting admin</span>
                      )
                    )}
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
  tabs: { display: 'flex', gap: 4, marginBottom: 20,
          background: '#fff', borderRadius: 10, padding: 4, width: 'fit-content',
          boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  tab: { padding: '9px 18px', fontSize: 13, fontWeight: 600, color: '#6B7280',
         borderRadius: 8, cursor: 'pointer' },
  tabActive: { background: '#1A3A5C', color: '#fff' },
  errorBanner: { background: '#FEE2E2', color: '#C0392B', padding: '10px 16px',
                 borderRadius: 8, fontSize: 13, marginBottom: 16 },
  tableWrap: { background: '#fff', borderRadius: 12, overflow: 'hidden',
               boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  table: { width: '100%', borderCollapse: 'collapse' },
  thead: { background: '#1A3A5C' },
  th: { padding: '14px 20px', textAlign: 'left', fontSize: 12,
        fontWeight: 700, color: '#fff' },
  trEven: { background: '#fff' },
  trOdd: { background: '#F9FAFB' },
  td: { padding: '14px 20px', fontSize: 13, color: '#374151',
        borderBottom: '1px solid #F3F4F6' },
  empty: { padding: 40, textAlign: 'center', color: '#9CA3AF', fontSize: 14 },
  badgePending: { background: '#FEF3C7', color: '#D07020', padding: '3px 10px',
                  borderRadius: 10, fontSize: 11, fontWeight: 700 },
  badgeOk: { background: '#D1FAE5', color: '#1A6E3C', padding: '3px 10px',
             borderRadius: 10, fontSize: 11, fontWeight: 700 },
  badgeRejected: { background: '#FEE2E2', color: '#C0392B', padding: '3px 10px',
                   borderRadius: 10, fontSize: 11, fontWeight: 700 },
  approveBtn: { background: '#1A6E3C', color: '#fff', border: 'none',
                borderRadius: 8, padding: '6px 12px', fontSize: 12,
                fontWeight: 600, cursor: 'pointer', display: 'flex',
                alignItems: 'center', gap: 4 },
  rejectBtn: { background: '#C0392B', color: '#fff', border: 'none',
               borderRadius: 8, padding: '6px 12px', fontSize: 12,
               fontWeight: 600, cursor: 'pointer', display: 'flex',
               alignItems: 'center', gap: 4 },
  btnIcon: { width: 12, height: 12 },
  viewOnlyNote: { fontSize: 11, color: '#9CA3AF', fontStyle: 'italic' },
};
