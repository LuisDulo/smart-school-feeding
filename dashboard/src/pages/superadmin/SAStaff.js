import React, { useState, useEffect } from 'react';
import { FiCheckCircle } from 'react-icons/fi';
import { superAdminAPI } from '../../services/superadminApi';

const ROLE_LABELS = { admin: 'School Admin', bursar: 'Bursar', kitchen: 'Kitchen Staff' };

export default function SAStaff() {
  const [schools, setSchools] = useState([]);
  const [staff, setStaff] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterSchoolId, setFilterSchoolId] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    school_id: '', role: 'kitchen', full_name: '', email: '', password: ''
  });
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const loadSchools = () => superAdminAPI.schools().then(r => setSchools(r.data.schools)).catch(() => {});
  const loadStaff = () => {
    setLoading(true);
    const params = filterSchoolId ? { school_id: filterSchoolId } : {};
    superAdminAPI.staff(params)
      .then(r => setStaff(r.data.staff))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadSchools(); }, []);
  useEffect(loadStaff, [filterSchoolId]);

  const update = (k, v) => setForm(p => ({ ...p, [k]: v }));

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!form.school_id || !form.full_name || !form.email || !form.password) {
      setError('All fields are required.');
      setMessage('');
      return;
    }
    setCreating(true);
    setError('');
    setMessage('');
    try {
      await superAdminAPI.createStaff(form);
      setMessage(`${ROLE_LABELS[form.role]} account created.`);
      setForm({ school_id: '', role: 'kitchen', full_name: '', email: '', password: '' });
      setShowCreate(false);
      loadStaff();
    } catch (e) {
      setError(e.response?.data?.error || 'Could not create account.');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div style={styles.page}>
      <div style={styles.topbar}>
        <div>
          <h1 style={styles.title}>Staff Management</h1>
          <p style={styles.subtitle}>Admins, bursars and kitchen staff across the network</p>
        </div>
        <button style={styles.createBtn} onClick={() => setShowCreate(v => !v)}>
          {showCreate ? 'Cancel' : '+ Add Staff Account'}
        </button>
      </div>

      <div style={styles.content}>
        {error && <div style={styles.errorMsg}>{error}</div>}
        {message && (
          <div style={styles.successMsg}>
            <FiCheckCircle style={styles.msgIcon} /> {message}
          </div>
        )}

        {showCreate && (
          <form style={styles.createForm} onSubmit={handleCreate}>
            <h3 style={styles.formTitle}>New Staff Account</h3>
            <div style={styles.formGrid}>
              <div style={styles.formField}>
                <label style={styles.formLabel}>School</label>
                <select style={styles.formInput} value={form.school_id} onChange={e => update('school_id', e.target.value)}>
                  <option value="">Select a school...</option>
                  {schools.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
              <div style={styles.formField}>
                <label style={styles.formLabel}>Role</label>
                <select style={styles.formInput} value={form.role} onChange={e => update('role', e.target.value)}>
                  <option value="kitchen">Kitchen Staff</option>
                  <option value="bursar">Bursar</option>
                  <option value="admin">School Admin</option>
                </select>
              </div>
              <div style={styles.formField}>
                <label style={styles.formLabel}>Full Name</label>
                <input style={styles.formInput} value={form.full_name} onChange={e => update('full_name', e.target.value)} />
              </div>
              <div style={styles.formField}>
                <label style={styles.formLabel}>Email</label>
                <input style={styles.formInput} type="email" value={form.email} onChange={e => update('email', e.target.value)} />
              </div>
              <div style={styles.formField}>
                <label style={styles.formLabel}>Password</label>
                <input style={styles.formInput} type="password" value={form.password} onChange={e => update('password', e.target.value)} minLength={8} />
              </div>
            </div>
            <div style={styles.formActions}>
              <button style={styles.submitBtn} type="submit" disabled={creating}>
                {creating ? 'Creating...' : 'Create Account'}
              </button>
            </div>
          </form>
        )}

        <div style={styles.filters}>
          <select style={styles.select} value={filterSchoolId} onChange={e => setFilterSchoolId(e.target.value)}>
            <option value="">All Schools</option>
            {schools.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>

        <div style={styles.tableCard}>
          <div style={{ overflowX: 'auto' }}>
            <table style={styles.table}>
              <thead>
                <tr style={styles.thead}>
                  {['Name', 'Email', 'Role', 'School', 'Since'].map(h => (
                    <th key={h} style={styles.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={5} style={styles.empty}>Loading...</td></tr>
                ) : staff.length === 0 ? (
                  <tr><td colSpan={5} style={styles.empty}>No staff found.</td></tr>
                ) : staff.map((u, i) => (
                  <tr key={u.id} style={i % 2 === 0 ? {} : { background: '#F9FAFB' }}>
                    <td style={{ ...styles.td, fontWeight: 700, color: '#1A3A5C' }}>{u.full_name}</td>
                    <td style={styles.td}>{u.email}</td>
                    <td style={styles.td}>
                      <span style={styles.roleBadge}>{ROLE_LABELS[u.role] || u.role}</span>
                    </td>
                    <td style={styles.td}>{u.school}</td>
                    <td style={styles.td}>{new Date(u.created_at).toLocaleDateString('en-KE')}</td>
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
  topbar: { background: '#1A3A5C', padding: '20px 32px', display: 'flex',
            justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 },
  title: { color: '#fff', fontSize: 22, fontWeight: 700, margin: 0 },
  subtitle: { color: '#6B9AB8', fontSize: 13, margin: '4px 0 0' },
  createBtn: { background: '#1A6E3C', color: '#fff', border: 'none', borderRadius: 8,
               padding: '10px 20px', fontSize: 13, fontWeight: 700, cursor: 'pointer' },
  content: { padding: 32 },
  errorMsg: { background: '#FEE2E2', color: '#C0392B', borderRadius: 8,
              padding: '12px 16px', fontSize: 14, marginBottom: 20 },
  successMsg: { background: '#D1FAE5', color: '#1A6E3C', borderRadius: 8,
                padding: '12px 16px', fontSize: 14, marginBottom: 20,
                display: 'flex', alignItems: 'center', gap: 8 },
  msgIcon: { width: 15, height: 15, flexShrink: 0 },
  createForm: { background: '#fff', borderRadius: 12, padding: 24, marginBottom: 24,
                boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  formTitle: { margin: '0 0 20px', fontSize: 16, fontWeight: 700, color: '#1A3A5C' },
  formGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 },
  formField: { display: 'flex', flexDirection: 'column', gap: 6 },
  formLabel: { fontSize: 12, fontWeight: 600, color: '#374151' },
  formInput: { border: '1px solid #E5E7EB', borderRadius: 8, padding: '10px 14px',
               fontSize: 14, outline: 'none', boxSizing: 'border-box' },
  formActions: { display: 'flex', gap: 12, marginTop: 20 },
  submitBtn: { background: '#1A6E3C', color: '#fff', border: 'none', borderRadius: 8,
               padding: '10px 24px', fontSize: 14, fontWeight: 700, cursor: 'pointer' },
  filters: { display: 'flex', gap: 10, marginBottom: 20 },
  select: { border: '1px solid #E5E7EB', borderRadius: 8, padding: '10px 14px',
            fontSize: 13, background: '#fff', outline: 'none' },
  tableCard: { background: '#fff', borderRadius: 12, overflow: 'hidden',
               boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  table: { width: '100%', borderCollapse: 'collapse', minWidth: 640 },
  thead: { background: '#1A3A5C' },
  th: { padding: '12px 16px', textAlign: 'left', fontSize: 11, fontWeight: 700, color: '#fff' },
  td: { padding: '12px 16px', fontSize: 13, color: '#374151', borderBottom: '1px solid #F3F4F6' },
  empty: { padding: 40, textAlign: 'center', color: '#9CA3AF' },
  roleBadge: { background: '#EEF0FB', color: '#3A4AB0', padding: '3px 10px',
               borderRadius: 10, fontSize: 11, fontWeight: 700 },
};
