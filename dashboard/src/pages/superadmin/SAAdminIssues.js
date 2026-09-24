import React, { useState, useEffect } from 'react';
import { FiCheckCircle, FiClock } from 'react-icons/fi';
import { superAdminAPI } from '../../services/superadminApi';

const FILTERS = [
  { key: '', label: 'All' },
  { key: 'open', label: 'Open' },
  { key: 'in_progress', label: 'In Progress' },
  { key: 'resolved', label: 'Resolved' },
];

const CATEGORY_LABELS = {
  technical: 'Technical / Platform Bug',
  billing: 'Billing & Payments',
  feature_request: 'Feature Request',
  data: 'Data / Reporting Issue',
  other: 'Other',
};

export default function SAAdminIssues() {
  const [filter, setFilter] = useState('open');
  const [issues, setIssues] = useState([]);
  const [openCount, setOpenCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeIssue, setActiveIssue] = useState(null);
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const load = () => {
    setLoading(true);
    superAdminAPI.adminIssues(filter)
      .then(res => {
        setIssues(res.data.issues);
        setOpenCount(res.data.open);
      })
      .catch(() => setError('Could not load reports.'))
      .finally(() => setLoading(false));
  };

  useEffect(load, [filter]);

  const openResolveModal = (issue) => {
    setActiveIssue(issue);
    setNotes('');
    setError('');
  };

  const handleUpdate = async (newStatus) => {
    if (!activeIssue) return;
    setSubmitting(true);
    setError('');
    try {
      await superAdminAPI.resolveAdminIssue(activeIssue.id, { status: newStatus, resolution_notes: notes });
      setActiveIssue(null);
      load();
    } catch (e) {
      setError(e.response?.data?.error || 'Could not update report.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={styles.page}>
      <div style={styles.topbar}>
        <h1 style={styles.title}>School Reports</h1>
        <p style={styles.subtitle}>Issues and reports raised by school admins across the network</p>
      </div>

      <div style={styles.content}>
        <div style={styles.tabs}>
          {FILTERS.map(f => (
            <div
              key={f.key}
              style={{ ...styles.tab, ...(filter === f.key ? styles.tabActive : {}) }}
              onClick={() => setFilter(f.key)}
            >
              {f.label}{f.key === 'open' && openCount > 0 ? ` (${openCount})` : ''}
            </div>
          ))}
        </div>

        {error && <div style={styles.errorBanner}>{error}</div>}

        <div style={styles.tableWrap}>
          <div style={{ overflowX: 'auto' }}>
          <table style={styles.table}>
            <thead>
              <tr style={styles.thead}>
                {['Subject', 'Category', 'School', 'Raised By', 'Status', ''].map(h => (
                  <th key={h} style={styles.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} style={styles.empty}>Loading...</td></tr>
              ) : issues.length === 0 ? (
                <tr><td colSpan={6} style={styles.empty}>No reports here.</td></tr>
              ) : issues.map((issue, i) => (
                <tr key={issue.id} style={i % 2 === 0 ? styles.trEven : styles.trOdd}>
                  <td style={{ ...styles.td, fontWeight: 600 }}>{issue.subject}</td>
                  <td style={styles.td}>{CATEGORY_LABELS[issue.category] || issue.category}</td>
                  <td style={{ ...styles.td, fontWeight: 600, color: '#1A3A5C' }}>{issue.school_name}</td>
                  <td style={styles.td}>
                    {issue.raised_by_name}
                    <div style={styles.subtle}>{issue.raised_by_email}</div>
                  </td>
                  <td style={styles.td}>
                    <span style={
                      issue.status === 'open' ? styles.badgeOpen
                      : issue.status === 'in_progress' ? styles.badgeProgress
                      : styles.badgeResolved
                    }>
                      {issue.status.replace('_', ' ')}
                    </span>
                  </td>
                  <td style={styles.td}>
                    {issue.status !== 'resolved' && (
                      <button style={styles.actionBtn} onClick={() => openResolveModal(issue)}>
                        Update
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
      </div>

      {activeIssue && (
        <div style={styles.modalOverlay} onClick={() => setActiveIssue(null)}>
          <div style={styles.modal} onClick={e => e.stopPropagation()}>
            <h3 style={styles.modalTitle}>{activeIssue.subject}</h3>
            <p style={styles.modalMeta}>
              {activeIssue.school_name} · {CATEGORY_LABELS[activeIssue.category]} · raised by{' '}
              {activeIssue.raised_by_name} ({activeIssue.raised_by_email})
            </p>
            <p style={styles.modalDesc}>{activeIssue.description}</p>

            <label style={styles.label}>Resolution notes</label>
            <textarea
              style={styles.textarea}
              rows={3}
              value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder="Optional notes for the school admin..."
            />

            {error && <div style={styles.errorBanner}>{error}</div>}

            <div style={styles.modalActions}>
              <button style={styles.cancelBtn} onClick={() => setActiveIssue(null)}>Close</button>
              {activeIssue.status === 'open' && (
                <button
                  style={styles.progressBtn}
                  disabled={submitting}
                  onClick={() => handleUpdate('in_progress')}
                >
                  <FiClock style={styles.btnIcon} /> Mark In Progress
                </button>
              )}
              <button
                style={styles.resolveBtn}
                disabled={submitting}
                onClick={() => handleUpdate('resolved')}
              >
                <FiCheckCircle style={styles.btnIcon} /> Mark Resolved
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  page: { flex: 1, display: 'flex', flexDirection: 'column',
          background: '#F7F9FC', overflow: 'auto' },
  topbar: { background: '#1A3A5C', padding: '20px 32px' },
  title: { color: '#fff', fontSize: 22, fontWeight: 700, margin: 0 },
  subtitle: { color: '#6B9AB8', fontSize: 13, margin: '4px 0 0' },
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
  table: { width: '100%', borderCollapse: 'collapse', minWidth: 760 },
  thead: { background: '#1A3A5C' },
  th: { padding: '14px 20px', textAlign: 'left', fontSize: 12,
        fontWeight: 700, color: '#fff' },
  trEven: { background: '#fff' },
  trOdd: { background: '#F9FAFB' },
  td: { padding: '14px 20px', fontSize: 13, color: '#374151',
        borderBottom: '1px solid #F3F4F6' },
  subtle: { fontSize: 11, color: '#9CA3AF', marginTop: 2 },
  empty: { padding: 40, textAlign: 'center', color: '#9CA3AF', fontSize: 14 },
  badgeOpen: { background: '#FEE2E2', color: '#C0392B', padding: '3px 10px',
               borderRadius: 10, fontSize: 11, fontWeight: 700 },
  badgeProgress: { background: '#FEF3C7', color: '#D07020', padding: '3px 10px',
                   borderRadius: 10, fontSize: 11, fontWeight: 700 },
  badgeResolved: { background: '#D1FAE5', color: '#1A6E3C', padding: '3px 10px',
                   borderRadius: 10, fontSize: 11, fontWeight: 700 },
  actionBtn: { background: '#1A3A5C', color: '#fff', border: 'none',
               borderRadius: 8, padding: '6px 14px', fontSize: 12,
               fontWeight: 600, cursor: 'pointer' },
  modalOverlay: { position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                  background: 'rgba(0,0,0,0.4)', display: 'flex',
                  alignItems: 'center', justifyContent: 'center', zIndex: 100 },
  modal: { background: '#fff', borderRadius: 12, padding: 28, width: 460,
           maxHeight: '80vh', overflow: 'auto',
           boxShadow: '0 8px 32px rgba(0,0,0,0.2)' },
  modalTitle: { margin: 0, fontSize: 18, fontWeight: 700, color: '#1A3A5C' },
  modalMeta: { margin: '6px 0 12px', fontSize: 12, color: '#6B7280' },
  modalDesc: { fontSize: 13, color: '#374151', background: '#F9FAFB',
               padding: 12, borderRadius: 8, lineHeight: 1.5 },
  label: { display: 'block', fontSize: 12, fontWeight: 600, color: '#374151',
           marginBottom: 6, marginTop: 16 },
  textarea: { width: '100%', border: '1px solid #E5E7EB', borderRadius: 8,
              padding: '10px 12px', fontSize: 13, boxSizing: 'border-box',
              outline: 'none', resize: 'vertical', fontFamily: 'inherit' },
  modalActions: { display: 'flex', gap: 8, marginTop: 20 },
  cancelBtn: { background: '#F3F4F6', color: '#374151', border: 'none',
               borderRadius: 8, padding: '10px 16px', fontSize: 13,
               fontWeight: 600, cursor: 'pointer' },
  progressBtn: { background: '#D07020', color: '#fff', border: 'none',
                 borderRadius: 8, padding: '10px 16px', fontSize: 13,
                 fontWeight: 600, cursor: 'pointer', display: 'flex',
                 alignItems: 'center', gap: 6 },
  resolveBtn: { background: '#1A6E3C', color: '#fff', border: 'none',
                borderRadius: 8, padding: '10px 16px', fontSize: 13,
                fontWeight: 600, cursor: 'pointer', display: 'flex',
                alignItems: 'center', gap: 6, marginLeft: 'auto' },
  btnIcon: { width: 13, height: 13 },
};
