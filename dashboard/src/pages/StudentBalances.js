import React, { useState, useEffect } from 'react';
import Topbar from '../components/Topbar';
import { paymentsAPI } from '../services/api';

export default function StudentBalances() {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');

  useEffect(() => {
    paymentsAPI.allBalances()
      .then(res => setStudents(res.data))
      .catch(e => console.error(e))
      .finally(() => setLoading(false));
  }, []);

  const filtered = students.filter(s => {
    const matchSearch = s.student_name
      .toLowerCase().includes(search.toLowerCase());
    if (filter === 'low') return matchSearch && s.is_low;
    if (filter === 'zero') return matchSearch && s.balance_cents === 0;
    return matchSearch;
  });

  const getStatusBadge = (s) => {
    if (s.balance_cents === 0)
      return { label: 'Inactive', bg: '#FEE2E2', color: '#C0392B' };
    if (s.is_low)
      return { label: 'Low', bg: '#FEF3C7', color: '#D07020' };
    return { label: 'Active', bg: '#D1FAE5', color: '#1A6E3C' };
  };

  return (
    <div style={styles.page}>
      <Topbar
        title="Student Balances"
        subtitle={`${students.length} students enrolled`}
      />
      <div style={styles.content}>
        <div style={styles.toolbar}>
          <input
            style={styles.search}
            placeholder="🔍  Search student name..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          <div style={styles.filters}>
            {['all', 'low', 'zero'].map(f => (
              <button
                key={f}
                style={{
                  ...styles.filterBtn,
                  ...(filter === f ? styles.filterBtnActive : {})
                }}
                onClick={() => setFilter(f)}
              >
                {f === 'all' ? 'All' :
                 f === 'low' ? '⚠️ Low Balance' : '❌ Zero Balance'}
              </button>
            ))}
          </div>
        </div>

        <div style={styles.tableWrap}>
          <table style={styles.table}>
            <thead>
              <tr style={styles.thead}>
                {['Student Name', 'Balance (KES)',
                  'Last Updated', 'Status'].map(h => (
                  <th key={h} style={styles.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={4} style={styles.empty}>Loading...</td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan={4} style={styles.empty}>No students found</td></tr>
              ) : filtered.map((s, i) => {
                const badge = getStatusBadge(s);
                return (
                  <tr key={s.id}
                    style={i % 2 === 0 ? styles.trEven : styles.trOdd}>
                    <td style={styles.td}>{s.student_name}</td>
                    <td style={{
                      ...styles.td,
                      fontWeight: 700,
                      color: s.balance_cents < 10000
                        ? '#C0392B' : '#1A3A5C'
                    }}>
                      {s.balance_ksh?.toLocaleString('en-KE',
                        { minimumFractionDigits: 2 })}
                    </td>
                    <td style={styles.td}>
                      {new Date(s.last_updated).toLocaleDateString('en-KE')}
                    </td>
                    <td style={styles.td}>
                      <span style={{
                        background: badge.bg,
                        color: badge.color,
                        padding: '3px 10px',
                        borderRadius: 10,
                        fontSize: 11,
                        fontWeight: 700
                      }}>
                        {badge.label}
                      </span>
                    </td>
                  </tr>
                );
              })}
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
  toolbar: { display: 'flex', gap: 16, marginBottom: 20,
             alignItems: 'center', flexWrap: 'wrap' },
  search: { border: '1px solid #E5E7EB', borderRadius: 8,
            padding: '10px 16px', fontSize: 14,
            width: 280, outline: 'none' },
  filters: { display: 'flex', gap: 8 },
  filterBtn: { border: '1px solid #E5E7EB', borderRadius: 8,
               padding: '8px 14px', fontSize: 12,
               cursor: 'pointer', background: '#fff',
               fontWeight: 600, color: '#374151' },
  filterBtnActive: { background: '#1A6E3C',
                     borderColor: '#1A6E3C', color: '#fff' },
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
  empty: { padding: 40, textAlign: 'center',
           color: '#9CA3AF', fontSize: 14 },
};
