import React, { useState, useEffect } from 'react';
import { superAdminAPI } from '../../services/superadminApi';

export default function SASchools({ onDrillDown }) {
  const [schools, setSchools] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    name: '', county: '', contact_email: '',
    admin_name: '', admin_email: '', admin_password: ''
  });
  const [creating, setCreating] = useState(false);
  const [msg, setMsg] = useState('');

  const load = () => {
    setLoading(true);
    superAdminAPI.schools()
      .then(r => setSchools(r.data.schools))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const update = (k, v) => setForm(p => ({ ...p, [k]: v }));

  const handleCreate = async () => {
    if (!form.name || !form.county || !form.contact_email) {
      setMsg('Name, county and contact email are required.');
      return;
    }
    setCreating(true);
    setMsg('');
    try {
      await superAdminAPI.createSchool(form);
      setMsg(`✅ School "${form.name}" created successfully.`);
      setForm({
        name: '', county: '', contact_email: '',
        admin_name: '', admin_email: '', admin_password: ''
      });
      setShowCreate(false);
      load();
    } catch (e) {
      setMsg(e.response?.data?.error || 'Creation failed.');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div style={styles.page}>
      <div style={styles.topbar}>
        <div>
          <h1 style={styles.title}>Schools Management</h1>
          <p style={styles.subtitle}>
            {schools.length} schools in the network
          </p>
        </div>
        <button
          style={styles.createBtn}
          onClick={() => setShowCreate(true)}
        >
          + Add New School
        </button>
      </div>

      <div style={styles.content}>
        {msg && (
          <div style={{
            ...styles.msg,
            background: msg.startsWith('✅')
              ? '#D1FAE5' : '#FEE2E2',
            color: msg.startsWith('✅')
              ? '#1A6E3C' : '#C0392B'
          }}>
            {msg}
          </div>
        )}

        {/* Create school form */}
        {showCreate && (
          <div style={styles.createForm}>
            <h3 style={styles.formTitle}>Register New School</h3>
            <div style={styles.formGrid}>
              {[
                { label: 'School Name *', key: 'name',
                  placeholder: 'Strathmore Primary School' },
                { label: 'County *', key: 'county',
                  placeholder: 'Nairobi' },
                { label: 'Contact Email *', key: 'contact_email',
                  placeholder: 'admin@school.ac.ke' },
                { label: 'Admin Full Name', key: 'admin_name',
                  placeholder: 'Grace Njoroge' },
                { label: 'Admin Email', key: 'admin_email',
                  placeholder: 'grace@school.ac.ke' },
                { label: 'Admin Password', key: 'admin_password',
                  placeholder: '••••••••', type: 'password' },
              ].map(f => (
                <div key={f.key} style={styles.formField}>
                  <label style={styles.formLabel}>{f.label}</label>
                  <input
                    style={styles.formInput}
                    type={f.type || 'text'}
                    placeholder={f.placeholder}
                    value={form[f.key]}
                    onChange={e => update(f.key, e.target.value)}
                  />
                </div>
              ))}
            </div>
            <div style={styles.formActions}>
              <button
                style={styles.submitBtn}
                onClick={handleCreate}
                disabled={creating}
              >
                {creating ? 'Creating...' : 'Create School'}
              </button>
              <button
                style={styles.cancelBtn}
                onClick={() => setShowCreate(false)}
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* School cards grid */}
        <div style={styles.schoolsGrid}>
          {loading ? (
            <p style={{ color: '#9CA3AF' }}>Loading schools...</p>
          ) : schools.length === 0 ? (
            <p style={{ color: '#9CA3AF' }}>No schools yet — add one above.</p>
          ) : schools.map(s => (
            <div key={s.id} style={styles.schoolCard}>
              <div style={styles.schoolHeader}>
                <span style={styles.schoolIcon}>🏫</span>
                <div>
                  <h4 style={styles.schoolName}>{s.name}</h4>
                  <p style={styles.schoolCounty}>
                    {s.county} · {s.contact_email}
                  </p>
                </div>
              </div>

              <div style={styles.schoolStats}>
                {[
                  { label: 'Students', val: s.student_count },
                  { label: 'Staff', val: s.staff_count },
                  { label: 'Meals Today', val: s.meals_today },
                  { label: 'Flags', val: s.pending_flags,
                    red: s.pending_flags > 0 },
                ].map(st => (
                  <div key={st.label} style={styles.schoolStat}>
                    <p style={{
                      ...styles.schoolStatVal,
                      color: st.red ? '#C0392B' : '#1A3A5C'
                    }}>
                      {st.val}
                    </p>
                    <p style={styles.schoolStatLabel}>{st.label}</p>
                  </div>
                ))}
              </div>

              <div style={styles.schoolBalance}>
                <span style={styles.balLabel}>Balance Pool</span>
                <span style={styles.balVal}>
                  KES {s.total_balance_pool_ksh?.toLocaleString()}
                </span>
              </div>

              <div style={styles.schoolBalance}>
                <span style={styles.balLabel}>Avg per Student</span>
                <span style={{
                  ...styles.balVal,
                  color: s.avg_balance_ksh < 100
                    ? '#C0392B' : '#1A6E3C'
                }}>
                  KES {s.avg_balance_ksh?.toFixed(2)}
                </span>
              </div>

              <button
                style={styles.viewBtn}
                onClick={() => onDrillDown(s.id, s.name)}
              >
                View School Dashboard →
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
  topbar: { background: '#1A3A5C', padding: '20px 32px',
            display: 'flex', justifyContent: 'space-between',
            alignItems: 'center', flexWrap: 'wrap', gap: 10 },
  title: { color: '#fff', fontSize: 22, fontWeight: 700, margin: 0 },
  subtitle: { color: '#6B9AB8', fontSize: 13, margin: '4px 0 0' },
  createBtn: { background: '#1A6E3C', color: '#fff', border: 'none',
               borderRadius: 8, padding: '10px 20px', fontSize: 13,
               fontWeight: 700, cursor: 'pointer' },
  content: { padding: 32 },
  msg: { borderRadius: 8, padding: '12px 16px',
         fontSize: 14, marginBottom: 20 },
  createForm: { background: '#fff', borderRadius: 12, padding: 24,
                marginBottom: 24,
                boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  formTitle: { margin: '0 0 20px', fontSize: 16,
               fontWeight: 700, color: '#1A3A5C' },
  formGrid: { display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: 16 },
  formField: { display: 'flex', flexDirection: 'column', gap: 6 },
  formLabel: { fontSize: 12, fontWeight: 600, color: '#374151' },
  formInput: { border: '1px solid #E5E7EB', borderRadius: 8,
               padding: '10px 14px', fontSize: 14, outline: 'none',
               boxSizing: 'border-box' },
  formActions: { display: 'flex', gap: 12, marginTop: 20 },
  submitBtn: { background: '#1A6E3C', color: '#fff', border: 'none',
               borderRadius: 8, padding: '10px 24px', fontSize: 14,
               fontWeight: 700, cursor: 'pointer' },
  cancelBtn: { background: '#fff', color: '#374151',
               border: '1px solid #E5E7EB', borderRadius: 8,
               padding: '10px 24px', fontSize: 14, cursor: 'pointer' },
  schoolsGrid: { display: 'grid',
                 gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                 gap: 20 },
  schoolCard: { background: '#fff', borderRadius: 12, padding: 24,
                boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  schoolHeader: { display: 'flex', gap: 12,
                  alignItems: 'flex-start', marginBottom: 16 },
  schoolIcon: { fontSize: 28 },
  schoolName: { margin: 0, fontSize: 15,
                fontWeight: 700, color: '#1A3A5C' },
  schoolCounty: { margin: '4px 0 0', fontSize: 11, color: '#6B7280' },
  schoolStats: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
                 gap: 8, marginBottom: 16 },
  schoolStat: { textAlign: 'center', padding: '8px 0',
                background: '#F7F9FC', borderRadius: 6 },
  schoolStatVal: { margin: 0, fontSize: 18, fontWeight: 700 },
  schoolStatLabel: { margin: '2px 0 0', fontSize: 10, color: '#6B7280' },
  schoolBalance: { display: 'flex', justifyContent: 'space-between',
                   padding: '8px 0',
                   borderBottom: '1px solid #F3F4F6' },
  balLabel: { fontSize: 12, color: '#6B7280' },
  balVal: { fontSize: 13, fontWeight: 700, color: '#1A3A5C' },
  viewBtn: { width: '100%', marginTop: 16, background: '#1A3A5C',
             color: '#fff', border: 'none', borderRadius: 8,
             padding: '10px', fontSize: 13, fontWeight: 700,
             cursor: 'pointer' },
};
