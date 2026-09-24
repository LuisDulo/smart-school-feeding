import React, { useState, useEffect } from 'react';
import { FiUserPlus, FiLink, FiPrinter, FiRefreshCw } from 'react-icons/fi';
import { MdOutlineQrCode2 } from 'react-icons/md';
import { QRCodeSVG } from 'qrcode.react';
import Topbar from '../components/Topbar';
import { adminAPI } from '../services/api';

const TABS = [
  { key: 'students', label: 'Students' },
  { key: 'parents', label: 'Parents' },
  { key: 'link', label: 'Link Parent to Student' },
];

export default function AccountManagement() {
  const [tab, setTab] = useState('students');
  const [students, setStudents] = useState([]);
  const [parents, setParents] = useState([]);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const loadStudents = () => adminAPI.listStudents().then(res => setStudents(res.data)).catch(() => {});
  const loadParents = () => adminAPI.listParents().then(res => setParents(res.data)).catch(() => {});

  useEffect(() => { loadStudents(); loadParents(); }, []);

  const flash = (msg) => {
    setMessage(msg);
    setTimeout(() => setMessage(''), 4000);
  };

  return (
    <div style={styles.page}>
      <Topbar title="Account Management" subtitle="Create student and parent accounts, and link families together" />
      <div style={styles.content}>
        <div style={styles.tabs}>
          {TABS.map(t => (
            <div
              key={t.key}
              style={{ ...styles.tab, ...(tab === t.key ? styles.tabActive : {}) }}
              onClick={() => setTab(t.key)}
            >
              {t.label}
            </div>
          ))}
        </div>

        {error && <div style={styles.errorBanner}>{error}</div>}
        {message && <div style={styles.successBanner}>{message}</div>}

        {tab === 'students' && (
          <StudentsTab
            students={students}
            onCreated={() => { loadStudents(); flash('Student account created.'); }}
            onQRChanged={() => { loadStudents(); flash('New QR code issued — the old card/wristband stops working.'); }}
            setError={setError}
          />
        )}
        {tab === 'parents' && (
          <ParentsTab
            parents={parents}
            students={students}
            onCreated={() => { loadParents(); flash('Parent account created.'); }}
            setError={setError}
          />
        )}
        {tab === 'link' && (
          <LinkTab
            parents={parents}
            students={students}
            onLinked={() => { loadParents(); loadStudents(); flash('Linked successfully.'); }}
            setError={setError}
          />
        )}
      </div>
    </div>
  );
}

function StudentsTab({ students, onCreated, onQRChanged, setError }) {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [balance, setBalance] = useState('0');
  const [submitting, setSubmitting] = useState(false);
  const [qrStudent, setQrStudent] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      await adminAPI.createStudent({
        full_name: fullName,
        email,
        password,
        starting_balance_cents: Math.round(parseFloat(balance || '0') * 100),
      });
      setFullName(''); setEmail(''); setPassword(''); setBalance('0');
      onCreated();
    } catch (e) {
      setError(JSON.stringify(e.response?.data) || 'Could not create student.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={styles.grid}>
      <form style={styles.card} onSubmit={handleSubmit}>
        <h3 style={styles.cardTitle}><FiUserPlus style={styles.cardIcon} /> New Student</h3>
        <label style={styles.label}>Full Name</label>
        <input style={styles.input} value={fullName} onChange={e => setFullName(e.target.value)} required />
        <label style={styles.label}>Email</label>
        <input style={styles.input} type="email" value={email} onChange={e => setEmail(e.target.value)} required />
        <label style={styles.label}>Password</label>
        <input style={styles.input} type="password" value={password} onChange={e => setPassword(e.target.value)} required minLength={8} />
        <label style={styles.label}>Starting Balance (KES)</label>
        <input style={styles.input} type="number" min="0" step="0.01" value={balance} onChange={e => setBalance(e.target.value)} />
        <button style={styles.submitBtn} type="submit" disabled={submitting}>
          {submitting ? 'Creating...' : 'Create Student Account'}
        </button>
      </form>

      <div style={styles.listCard}>
        <h3 style={styles.cardTitle}>Students ({students.length})</h3>
        <div style={styles.list}>
          {students.map(s => (
            <div key={s.id} style={styles.listRow}>
              <div>
                <div style={styles.listName}>{s.full_name}</div>
                <div style={styles.listSub}>{s.email}</div>
                {s.guardian_names.length > 0 && (
                  <div style={styles.listSub}>Guardians: {s.guardian_names.join(', ')}</div>
                )}
              </div>
              <div style={styles.listRight}>
                <div style={styles.listBalance}>
                  {s.balance_cents != null ? `KES ${(s.balance_cents / 100).toFixed(2)}` : '—'}
                </div>
                {s.qr_token && (
                  <button style={styles.qrBtn} onClick={() => setQrStudent(s)}>
                    <MdOutlineQrCode2 style={styles.qrBtnIcon} /> QR Card
                  </button>
                )}
              </div>
            </div>
          ))}
          {students.length === 0 && <div style={styles.empty}>No students yet.</div>}
        </div>
      </div>

      {qrStudent && (
        <QRCardModal
          student={qrStudent}
          onClose={() => setQrStudent(null)}
          onRegenerated={(updated) => {
            setQrStudent(updated);
            onQRChanged();
          }}
          setError={setError}
        />
      )}
    </div>
  );
}

function QRCardModal({ student, onClose, onRegenerated, setError }) {
  const [regenerating, setRegenerating] = useState(false);

  const handleRegenerate = async () => {
    if (!window.confirm(
      `Issue a new QR code for ${student.full_name}? ` +
      `Their current card/wristband will stop working immediately.`
    )) return;
    setRegenerating(true);
    setError('');
    try {
      const res = await adminAPI.regenerateQR(student.id);
      onRegenerated({ ...student, qr_token: res.data.qr_token });
    } catch (e) {
      setError(e.response?.data?.error || 'Could not regenerate QR code.');
    } finally {
      setRegenerating(false);
    }
  };

  return (
    <div style={styles.modalOverlay} onClick={onClose}>
      <div style={styles.qrModal} onClick={e => e.stopPropagation()}>
        <style>{`
          @media print {
            body * { visibility: hidden; }
            #qr-print-area, #qr-print-area * { visibility: visible; }
            #qr-print-area { position: fixed; top: 40px; left: 0; right: 0;
                             display: flex; justify-content: center; }
          }
        `}</style>
        <div id="qr-print-area" style={styles.qrCard}>
          <QRCodeSVG value={student.qr_token} size={180} level="M" />
          <p style={styles.qrCardName}>{student.full_name}</p>
          <p style={styles.qrCardSub}>Scan at the serving counter</p>
        </div>

        <div style={styles.modalActions}>
          <button style={styles.printBtn} onClick={() => window.print()}>
            <FiPrinter style={styles.btnIcon} /> Print Card
          </button>
          <button style={styles.regenBtn} onClick={handleRegenerate} disabled={regenerating}>
            <FiRefreshCw style={styles.btnIcon} />
            {regenerating ? 'Issuing...' : 'Lost Card — Issue New Code'}
          </button>
          <button style={styles.closeBtn} onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}

function ParentsTab({ parents, students, onCreated, setError }) {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [studentIds, setStudentIds] = useState([]);
  const [submitting, setSubmitting] = useState(false);

  const toggleStudent = (id) => {
    setStudentIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      await adminAPI.createParent({
        full_name: fullName,
        email,
        password,
        student_ids: studentIds,
      });
      setFullName(''); setEmail(''); setPassword(''); setStudentIds([]);
      onCreated();
    } catch (e) {
      setError(JSON.stringify(e.response?.data) || 'Could not create parent.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={styles.grid}>
      <form style={styles.card} onSubmit={handleSubmit}>
        <h3 style={styles.cardTitle}><FiUserPlus style={styles.cardIcon} /> New Parent</h3>
        <label style={styles.label}>Full Name</label>
        <input style={styles.input} value={fullName} onChange={e => setFullName(e.target.value)} required />
        <label style={styles.label}>Email</label>
        <input style={styles.input} type="email" value={email} onChange={e => setEmail(e.target.value)} required />
        <label style={styles.label}>Password</label>
        <input style={styles.input} type="password" value={password} onChange={e => setPassword(e.target.value)} required minLength={8} />
        <label style={styles.label}>Link to Student(s) (optional)</label>
        <div style={styles.checkList}>
          {students.map(s => (
            <label key={s.id} style={styles.checkRow}>
              <input type="checkbox" checked={studentIds.includes(s.id)} onChange={() => toggleStudent(s.id)} />
              {s.full_name}
            </label>
          ))}
          {students.length === 0 && <div style={styles.empty}>No students to link yet.</div>}
        </div>
        <button style={styles.submitBtn} type="submit" disabled={submitting}>
          {submitting ? 'Creating...' : 'Create Parent Account'}
        </button>
      </form>

      <div style={styles.listCard}>
        <h3 style={styles.cardTitle}>Parents ({parents.length})</h3>
        <div style={styles.list}>
          {parents.map(p => (
            <div key={p.id} style={styles.listRow}>
              <div>
                <div style={styles.listName}>{p.full_name}</div>
                <div style={styles.listSub}>{p.email}</div>
              </div>
              <div style={styles.listSub}>
                {p.linked_students.length > 0
                  ? p.linked_students.map(s => s.full_name).join(', ')
                  : 'No children linked'}
              </div>
            </div>
          ))}
          {parents.length === 0 && <div style={styles.empty}>No parents yet.</div>}
        </div>
      </div>
    </div>
  );
}

function LinkTab({ parents, students, onLinked, setError }) {
  const [parentId, setParentId] = useState('');
  const [studentId, setStudentId] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleLink = async (e) => {
    e.preventDefault();
    if (!parentId || !studentId) return;
    setSubmitting(true);
    setError('');
    try {
      await adminAPI.linkGuardian({ parent_id: Number(parentId), student_id: Number(studentId) });
      setParentId(''); setStudentId('');
      onLinked();
    } catch (e) {
      setError(JSON.stringify(e.response?.data) || 'Could not link.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form style={styles.card} onSubmit={handleLink}>
      <h3 style={styles.cardTitle}><FiLink style={styles.cardIcon} /> Link Parent to Student</h3>
      <label style={styles.label}>Parent</label>
      <select style={styles.input} value={parentId} onChange={e => setParentId(e.target.value)} required>
        <option value="">Select a parent...</option>
        {parents.map(p => <option key={p.id} value={p.id}>{p.full_name} ({p.email})</option>)}
      </select>
      <label style={styles.label}>Student</label>
      <select style={styles.input} value={studentId} onChange={e => setStudentId(e.target.value)} required>
        <option value="">Select a student...</option>
        {students.map(s => <option key={s.id} value={s.id}>{s.full_name} ({s.email})</option>)}
      </select>
      <button style={styles.submitBtn} type="submit" disabled={submitting}>
        {submitting ? 'Linking...' : 'Link Guardian'}
      </button>
    </form>
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
                 borderRadius: 8, fontSize: 13, marginBottom: 16, wordBreak: 'break-word' },
  successBanner: { background: '#D1FAE5', color: '#1A6E3C', padding: '10px 16px',
                   borderRadius: 8, fontSize: 13, marginBottom: 16 },
  grid: { display: 'grid', gridTemplateColumns: '380px 1fr', gap: 20 },
  card: { background: '#fff', borderRadius: 12, padding: 24,
          boxShadow: '0 2px 8px rgba(0,0,0,0.04)', height: 'fit-content' },
  cardTitle: { margin: '0 0 16px', fontSize: 15, fontWeight: 700, color: '#1A3A5C',
               display: 'flex', alignItems: 'center', gap: 8 },
  cardIcon: { width: 16, height: 16 },
  label: { display: 'block', fontSize: 12, fontWeight: 600, color: '#374151',
           marginBottom: 6, marginTop: 14 },
  input: { width: '100%', border: '1px solid #E5E7EB', borderRadius: 8,
           padding: '10px 12px', fontSize: 13, boxSizing: 'border-box', outline: 'none' },
  checkList: { maxHeight: 160, overflow: 'auto', border: '1px solid #F3F4F6',
               borderRadius: 8, padding: 8 },
  checkRow: { display: 'flex', alignItems: 'center', gap: 8, padding: '6px 4px',
              fontSize: 13, color: '#374151', cursor: 'pointer' },
  submitBtn: { width: '100%', background: '#1A6E3C', color: '#fff', border: 'none',
               borderRadius: 8, padding: '11px 16px', fontSize: 13,
               fontWeight: 700, marginTop: 18, cursor: 'pointer' },
  listCard: { background: '#fff', borderRadius: 12, padding: 24,
              boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  list: { display: 'flex', flexDirection: 'column', gap: 2, maxHeight: 480, overflow: 'auto' },
  listRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center',
             padding: '12px 8px', borderBottom: '1px solid #F3F4F6' },
  listName: { fontSize: 13, fontWeight: 600, color: '#1A3A5C' },
  listSub: { fontSize: 12, color: '#6B7280', marginTop: 2 },
  listRight: { display: 'flex', flexDirection: 'column',
               alignItems: 'flex-end', gap: 6 },
  listBalance: { fontSize: 13, fontWeight: 700, color: '#1A3A5C' },
  qrBtn: { background: '#EEF0FB', color: '#3A4AB0', border: 'none',
           borderRadius: 6, padding: '4px 10px', fontSize: 11,
           fontWeight: 700, cursor: 'pointer', display: 'flex',
           alignItems: 'center', gap: 4 },
  qrBtnIcon: { width: 13, height: 13 },
  empty: { padding: 20, textAlign: 'center', color: '#9CA3AF', fontSize: 13 },
  modalOverlay: { position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                  background: 'rgba(0,0,0,0.4)', display: 'flex',
                  alignItems: 'center', justifyContent: 'center', zIndex: 100 },
  qrModal: { background: '#fff', borderRadius: 12, padding: 28, width: 320,
             boxShadow: '0 8px 32px rgba(0,0,0,0.2)', textAlign: 'center' },
  qrCard: { display: 'flex', flexDirection: 'column', alignItems: 'center',
            gap: 8, padding: 16 },
  qrCardName: { margin: 0, fontSize: 16, fontWeight: 700, color: '#1A3A5C' },
  qrCardSub: { margin: 0, fontSize: 12, color: '#6B7280' },
  modalActions: { display: 'flex', flexDirection: 'column', gap: 8, marginTop: 16 },
  printBtn: { background: '#1A6E3C', color: '#fff', border: 'none',
              borderRadius: 8, padding: '10px 16px', fontSize: 13,
              fontWeight: 700, cursor: 'pointer', display: 'flex',
              alignItems: 'center', justifyContent: 'center', gap: 8 },
  regenBtn: { background: '#FEE2E2', color: '#C0392B', border: 'none',
              borderRadius: 8, padding: '10px 16px', fontSize: 13,
              fontWeight: 700, cursor: 'pointer', display: 'flex',
              alignItems: 'center', justifyContent: 'center', gap: 8 },
  closeBtn: { background: '#F3F4F6', color: '#374151', border: 'none',
              borderRadius: 8, padding: '10px 16px', fontSize: 13,
              fontWeight: 600, cursor: 'pointer' },
  btnIcon: { width: 14, height: 14 },
};
