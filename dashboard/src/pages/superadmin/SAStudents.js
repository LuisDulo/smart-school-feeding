import React, { useState, useEffect } from 'react';
import { superAdminAPI } from '../../services/superadminApi';

export default function SAStudents() {
  const [schools, setSchools] = useState([]);
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [schoolId, setSchoolId] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [query, setQuery] = useState('');

  useEffect(() => {
    superAdminAPI.schools().then(r => setSchools(r.data.schools)).catch(() => {});
  }, []);

  const load = () => {
    setLoading(true);
    const params = {};
    if (schoolId) params.school_id = schoolId;
    if (statusFilter) params.status = statusFilter;
    if (query.trim()) params.q = query.trim();
    superAdminAPI.students(params)
      .then(r => setStudents(r.data.students))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(load, [schoolId, statusFilter]);

  const handleSearch = (e) => {
    e.preventDefault();
    load();
  };

  return (
    <div style={styles.page}>
      <div style={styles.topbar}>
        <h1 style={styles.title}>All Students</h1>
        <p style={styles.subtitle}>Every student across the network</p>
      </div>

      <div style={styles.content}>
        <form style={styles.filters} onSubmit={handleSearch}>
          <select style={styles.select} value={schoolId} onChange={e => setSchoolId(e.target.value)}>
            <option value="">All Schools</option>
            {schools.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <select style={styles.select} value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
            <option value="">Any Balance</option>
            <option value="low">Low Balance</option>
            <option value="zero">Zero Balance</option>
          </select>
          <input
            style={styles.searchInput}
            placeholder="Search by name..."
            value={query}
            onChange={e => setQuery(e.target.value)}
          />
          <button type="submit" style={styles.searchBtn}>Search</button>
        </form>

        <div style={styles.tableCard}>
          <div style={{ overflowX: 'auto' }}>
            <table style={styles.table}>
              <thead>
                <tr style={styles.thead}>
                  {['Student', 'Email', 'School', 'Balance (KES)', 'Last Meal', 'Status'].map(h => (
                    <th key={h} style={styles.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={6} style={styles.empty}>Loading...</td></tr>
                ) : students.length === 0 ? (
                  <tr><td colSpan={6} style={styles.empty}>No students match.</td></tr>
                ) : students.map((s, i) => (
                  <tr key={s.id} style={i % 2 === 0 ? {} : { background: '#F9FAFB' }}>
                    <td style={{ ...styles.td, fontWeight: 700, color: '#1A3A5C' }}>{s.full_name}</td>
                    <td style={styles.td}>{s.email}</td>
                    <td style={styles.td}>{s.school}</td>
                    <td style={{
                      ...styles.td, fontWeight: 700,
                      color: s.is_zero ? '#C0392B' : s.is_low ? '#D07020' : '#1A6E3C'
                    }}>
                      {s.balance_ksh?.toLocaleString('en-KE', { minimumFractionDigits: 2 })}
                    </td>
                    <td style={styles.td}>{s.last_meal || '—'}</td>
                    <td style={styles.td}>
                      {s.is_zero ? (
                        <span style={styles.badgeRed}>Zero</span>
                      ) : s.is_low ? (
                        <span style={styles.badgeAmber}>Low</span>
                      ) : (
                        <span style={styles.badgeGreen}>OK</span>
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
  filters: { display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' },
  select: { border: '1px solid #E5E7EB', borderRadius: 8, padding: '10px 14px',
            fontSize: 13, background: '#fff', outline: 'none' },
  searchInput: { border: '1px solid #E5E7EB', borderRadius: 8, padding: '10px 14px',
                 fontSize: 13, outline: 'none', flex: 1, minWidth: 180 },
  searchBtn: { background: '#1A3A5C', color: '#fff', border: 'none', borderRadius: 8,
               padding: '10px 20px', fontSize: 13, fontWeight: 700, cursor: 'pointer' },
  tableCard: { background: '#fff', borderRadius: 12, overflow: 'hidden',
               boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  table: { width: '100%', borderCollapse: 'collapse', minWidth: 700 },
  thead: { background: '#1A3A5C' },
  th: { padding: '12px 16px', textAlign: 'left', fontSize: 11, fontWeight: 700, color: '#fff' },
  td: { padding: '12px 16px', fontSize: 13, color: '#374151', borderBottom: '1px solid #F3F4F6' },
  empty: { padding: 40, textAlign: 'center', color: '#9CA3AF' },
  badgeGreen: { background: '#D1FAE5', color: '#1A6E3C', padding: '3px 10px', borderRadius: 10, fontSize: 11, fontWeight: 700 },
  badgeAmber: { background: '#FEF3C7', color: '#D07020', padding: '3px 10px', borderRadius: 10, fontSize: 11, fontWeight: 700 },
  badgeRed: { background: '#FEE2E2', color: '#C0392B', padding: '3px 10px', borderRadius: 10, fontSize: 11, fontWeight: 700 },
};
