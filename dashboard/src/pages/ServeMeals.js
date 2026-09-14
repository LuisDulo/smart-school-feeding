import React, { useState } from 'react';
import { FiSearch, FiCheckCircle } from 'react-icons/fi';
import Topbar from '../components/Topbar';
import { mealsAPI } from '../services/api';

export default function ServeMeals() {
  const [query, setQuery] = useState('');
  const [students, setStudents] = useState([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [servingId, setServingId] = useState(null);
  const [error, setError] = useState('');
  const [lastServed, setLastServed] = useState(null);

  const runSearch = async (q) => {
    setQuery(q);
    if (!q || q.trim().length < 2) {
      setStudents([]);
      setSearched(false);
      setError('');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const res = await mealsAPI.lookup(q.trim());
      setStudents(res.data.students);
      setSearched(true);
    } catch (e) {
      setError(
        e.response?.status === 403
          ? 'Only kitchen staff accounts can serve meals.'
          : (e.response?.data?.error || 'Search failed.')
      );
      setStudents([]);
    } finally {
      setLoading(false);
    }
  };

  const handleServe = async (student) => {
    if (!window.confirm(
      `Serve a meal to ${student.full_name}? KES 50.00 will be deducted ` +
      `(balance: KES ${student.balance_ksh.toFixed(2)}).`
    )) return;

    setServingId(student.id);
    try {
      const res = await mealsAPI.serve(student.id);
      setLastServed(res.data);
      runSearch(query);
    } catch (e) {
      setError(e.response?.data?.error || 'Could not record meal.');
    } finally {
      setServingId(null);
    }
  };

  return (
    <div style={styles.page}>
      <Topbar
        title="Serve Meals"
        subtitle="Search a student and record a meal"
      />
      <div style={styles.content}>
        <div style={styles.searchWrap}>
          <FiSearch style={styles.searchIcon} />
          <input
            style={styles.search}
            placeholder="Search student by name..."
            value={query}
            onChange={e => runSearch(e.target.value)}
          />
        </div>

        {error && <div style={styles.errorBanner}>{error}</div>}

        {lastServed && (
          <div style={styles.successBanner}>
            <FiCheckCircle style={styles.bannerIcon} />
            Meal recorded for <strong>{lastServed.student}</strong> —
            new balance KES {lastServed.new_balance_ksh.toFixed(2)}
          </div>
        )}

        <div style={styles.tableWrap}>
          <table style={styles.table}>
            <thead>
              <tr style={styles.thead}>
                {['Student Name', 'Balance (KES)', 'Status', ''].map(h => (
                  <th key={h} style={styles.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={4} style={styles.empty}>Searching...</td></tr>
              ) : !searched ? (
                <tr><td colSpan={4} style={styles.empty}>
                  Type at least 2 letters of a student's name
                </td></tr>
              ) : students.length === 0 ? (
                <tr><td colSpan={4} style={styles.empty}>No students found</td></tr>
              ) : students.map((s, i) => (
                <tr key={s.id} style={i % 2 === 0 ? styles.trEven : styles.trOdd}>
                  <td style={{ ...styles.td, fontWeight: 600 }}>{s.full_name}</td>
                  <td style={{
                    ...styles.td,
                    fontWeight: 700,
                    color: s.is_low_balance ? '#C0392B' : '#1A3A5C'
                  }}>
                    {s.balance_ksh.toLocaleString('en-KE', { minimumFractionDigits: 2 })}
                  </td>
                  <td style={styles.td}>
                    {s.already_served_today ? (
                      <span style={styles.badgeServed}>Already served</span>
                    ) : s.is_low_balance ? (
                      <span style={styles.badgeLow}>Low balance</span>
                    ) : (
                      <span style={styles.badgeOk}>Eligible</span>
                    )}
                  </td>
                  <td style={styles.td}>
                    <button
                      style={{
                        ...styles.serveBtn,
                        ...(!s.eligible || servingId === s.id ? styles.serveBtnDisabled : {})
                      }}
                      disabled={!s.eligible || servingId === s.id}
                      onClick={() => handleServe(s)}
                    >
                      {servingId === s.id ? 'Serving...' : 'Serve Meal'}
                    </button>
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
  searchWrap: { position: 'relative', width: 320, marginBottom: 16 },
  searchIcon: { position: 'absolute', left: 12, top: '50%',
                transform: 'translateY(-50%)', width: 15, height: 15,
                color: '#9CA3AF' },
  search: { border: '1px solid #E5E7EB', borderRadius: 8,
            padding: '10px 16px 10px 36px', fontSize: 14,
            width: '100%', outline: 'none', boxSizing: 'border-box' },
  errorBanner: { background: '#FEE2E2', color: '#C0392B', padding: '10px 16px',
                 borderRadius: 8, fontSize: 13, marginBottom: 16 },
  successBanner: { background: '#D1FAE5', color: '#1A6E3C', padding: '10px 16px',
                   borderRadius: 8, fontSize: 13, marginBottom: 16,
                   display: 'flex', alignItems: 'center', gap: 8 },
  bannerIcon: { width: 15, height: 15, flexShrink: 0 },
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
  badgeServed: { background: '#F0F4F8', color: '#5A6A7A', padding: '3px 10px',
                 borderRadius: 10, fontSize: 11, fontWeight: 700 },
  badgeLow: { background: '#FEF3C7', color: '#D07020', padding: '3px 10px',
              borderRadius: 10, fontSize: 11, fontWeight: 700 },
  badgeOk: { background: '#D1FAE5', color: '#1A6E3C', padding: '3px 10px',
             borderRadius: 10, fontSize: 11, fontWeight: 700 },
  serveBtn: { background: '#1A6E3C', color: '#fff', border: 'none',
              borderRadius: 8, padding: '8px 16px', fontSize: 12,
              fontWeight: 600, cursor: 'pointer' },
  serveBtnDisabled: { background: '#CBD5E1', cursor: 'not-allowed' },
};
