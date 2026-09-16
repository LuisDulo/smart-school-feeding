import React, { useState, useEffect } from 'react';
import { FiSend, FiCheckCircle, FiClock } from 'react-icons/fi';
import Topbar from '../components/Topbar';
import { platformSupportAPI } from '../services/api';

const CATEGORIES = [
  { key: 'technical', label: 'Technical / Platform Bug' },
  { key: 'billing', label: 'Billing & Payments' },
  { key: 'feature_request', label: 'Feature Request' },
  { key: 'data', label: 'Data / Reporting Issue' },
  { key: 'other', label: 'Other' },
];

const CATEGORY_LABELS = Object.fromEntries(CATEGORIES.map(c => [c.key, c.label]));

export default function PlatformSupport() {
  const [category, setCategory] = useState('technical');
  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    platformSupportAPI.myIssues()
      .then(res => setIssues(res.data))
      .catch(() => setError('Could not load your reports.'))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!subject.trim() || !description.trim()) {
      setError('Please enter a subject and description.');
      return;
    }
    setSubmitting(true);
    setError('');
    setMessage('');
    try {
      await platformSupportAPI.raiseIssue({
        category, subject: subject.trim(), description: description.trim(),
      });
      setMessage('Report submitted to Webmasters Kenya.');
      setSubject('');
      setDescription('');
      setCategory('technical');
      load();
    } catch (e) {
      setError(e.response?.data?.error || 'Could not submit report.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={styles.page}>
      <Topbar
        title="Platform Support"
        subtitle="Raise a report or question directly with the Webmasters Kenya team"
      />
      <div style={styles.content}>
        <div style={styles.grid}>
          <form style={styles.card} onSubmit={handleSubmit}>
            <h3 style={styles.cardTitle}>New Report</h3>

            <label style={styles.label}>Category</label>
            <select
              style={styles.input}
              value={category}
              onChange={e => setCategory(e.target.value)}
            >
              {CATEGORIES.map(c => (
                <option key={c.key} value={c.key}>{c.label}</option>
              ))}
            </select>

            <label style={styles.label}>Subject</label>
            <input
              style={styles.input}
              placeholder="Short summary"
              value={subject}
              onChange={e => setSubject(e.target.value)}
            />

            <label style={styles.label}>Description</label>
            <textarea
              style={styles.textarea}
              rows={5}
              placeholder="Describe the issue or request in detail..."
              value={description}
              onChange={e => setDescription(e.target.value)}
            />

            {error && <div style={styles.errorBanner}>{error}</div>}
            {message && <div style={styles.successBanner}>{message}</div>}

            <button style={styles.submitBtn} type="submit" disabled={submitting}>
              <FiSend style={styles.btnIcon} />
              {submitting ? 'Submitting...' : 'Submit Report'}
            </button>
          </form>

          <div style={styles.listCard}>
            <h3 style={styles.cardTitle}>Your Reports ({issues.length})</h3>
            <div style={styles.list}>
              {loading ? (
                <p style={styles.empty}>Loading...</p>
              ) : issues.length === 0 ? (
                <p style={styles.empty}>No reports raised yet.</p>
              ) : issues.map(issue => (
                <div key={issue.id} style={styles.issueRow}>
                  <div style={styles.issueTop}>
                    <span style={styles.issueSubject}>{issue.subject}</span>
                    <span style={
                      issue.status === 'open' ? styles.badgeOpen
                      : issue.status === 'in_progress' ? styles.badgeProgress
                      : styles.badgeResolved
                    }>
                      {issue.status.replace('_', ' ')}
                    </span>
                  </div>
                  <p style={styles.issueMeta}>
                    {CATEGORY_LABELS[issue.category] || issue.category} ·{' '}
                    {new Date(issue.created_at).toLocaleDateString('en-KE', {
                      day: 'numeric', month: 'short', year: 'numeric',
                    })}
                  </p>
                  <p style={styles.issueDesc}>{issue.description}</p>
                  {issue.resolution_notes && (
                    <div style={styles.resolutionNote}>
                      {issue.status === 'resolved'
                        ? <FiCheckCircle style={styles.noteIcon} />
                        : <FiClock style={styles.noteIcon} />}
                      <span>
                        <strong>Webmasters Kenya:</strong> {issue.resolution_notes}
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

const styles = {
  page: { flex: 1, display: 'flex', flexDirection: 'column',
          background: '#F7F9FC', overflow: 'auto' },
  content: { padding: 32 },
  grid: { display: 'grid', gridTemplateColumns: '380px 1fr', gap: 20 },
  card: { background: '#fff', borderRadius: 12, padding: 24,
          boxShadow: '0 2px 8px rgba(0,0,0,0.04)', height: 'fit-content' },
  cardTitle: { margin: '0 0 16px', fontSize: 15, fontWeight: 700, color: '#1A3A5C' },
  label: { display: 'block', fontSize: 12, fontWeight: 600, color: '#374151',
           marginBottom: 6, marginTop: 14 },
  input: { width: '100%', border: '1px solid #E5E7EB', borderRadius: 8,
           padding: '10px 12px', fontSize: 13, boxSizing: 'border-box', outline: 'none' },
  textarea: { width: '100%', border: '1px solid #E5E7EB', borderRadius: 8,
              padding: '10px 12px', fontSize: 13, boxSizing: 'border-box',
              outline: 'none', resize: 'vertical', fontFamily: 'inherit' },
  errorBanner: { background: '#FEE2E2', color: '#C0392B', padding: '10px 16px',
                 borderRadius: 8, fontSize: 13, marginTop: 16 },
  successBanner: { background: '#D1FAE5', color: '#1A6E3C', padding: '10px 16px',
                   borderRadius: 8, fontSize: 13, marginTop: 16 },
  submitBtn: { width: '100%', background: '#1A6E3C', color: '#fff', border: 'none',
               borderRadius: 8, padding: '11px 16px', fontSize: 13,
               fontWeight: 700, marginTop: 18, cursor: 'pointer',
               display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 },
  btnIcon: { width: 14, height: 14 },
  listCard: { background: '#fff', borderRadius: 12, padding: 24,
              boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  list: { display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 560, overflow: 'auto' },
  empty: { color: '#9CA3AF', fontSize: 13, textAlign: 'center', padding: 20 },
  issueRow: { padding: '14px 8px', borderBottom: '1px solid #F3F4F6' },
  issueTop: { display: 'flex', justifyContent: 'space-between',
              alignItems: 'center', gap: 8 },
  issueSubject: { fontSize: 14, fontWeight: 700, color: '#1A3A5C' },
  issueMeta: { margin: '4px 0 0', fontSize: 11, color: '#9CA3AF' },
  issueDesc: { margin: '8px 0 0', fontSize: 13, color: '#374151', lineHeight: 1.5 },
  resolutionNote: { marginTop: 10, background: '#F0F4F8', borderRadius: 8,
                    padding: '10px 12px', fontSize: 12, color: '#374151',
                    display: 'flex', alignItems: 'flex-start', gap: 8, lineHeight: 1.5 },
  noteIcon: { width: 14, height: 14, flexShrink: 0, marginTop: 1, color: '#1A6E3C' },
  badgeOpen: { background: '#FEE2E2', color: '#C0392B', padding: '3px 10px',
               borderRadius: 10, fontSize: 11, fontWeight: 700, whiteSpace: 'nowrap' },
  badgeProgress: { background: '#FEF3C7', color: '#D07020', padding: '3px 10px',
                   borderRadius: 10, fontSize: 11, fontWeight: 700, whiteSpace: 'nowrap' },
  badgeResolved: { background: '#D1FAE5', color: '#1A6E3C', padding: '3px 10px',
                   borderRadius: 10, fontSize: 11, fontWeight: 700, whiteSpace: 'nowrap' },
};
