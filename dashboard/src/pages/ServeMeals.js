import React, { useState, useEffect } from 'react';
import { FiSearch, FiCheckCircle } from 'react-icons/fi';
import Topbar from '../components/Topbar';
import { mealsAPI } from '../services/api';

export default function ServeMeals() {
  const [query, setQuery] = useState('');
  const [students, setStudents] = useState([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [lastServed, setLastServed] = useState(null);

  const [menuItems, setMenuItems] = useState([]);
  const [combos, setCombos] = useState([]);
  const [servingStudent, setServingStudent] = useState(null);
  const [selectedItems, setSelectedItems] = useState([]);
  const [itemSearch, setItemSearch] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    mealsAPI.menuList().then(res => setMenuItems(res.data)).catch(() => {});
    mealsAPI.comboList().then(res => setCombos(res.data)).catch(() => {});
  }, []);

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

  const openServeModal = (student) => {
    setServingStudent(student);
    setSelectedItems([]);
    setItemSearch('');
    setError('');
  };

  const toggleItem = (itemId) => {
    setSelectedItems(prev =>
      prev.includes(itemId) ? prev.filter(id => id !== itemId) : [...prev, itemId]
    );
  };

  const addCombo = (combo) => {
    setSelectedItems(prev => {
      const comboItemIds = combo.items.map(i => i.id);
      const merged = new Set(prev);
      comboItemIds.forEach(id => merged.add(id));
      return Array.from(merged);
    });
  };

  const totalCents = selectedItems.reduce((sum, id) => {
    const item = menuItems.find(m => m.id === id);
    return sum + (item ? item.price_cents : 0);
  }, 0);

  const searchLower = itemSearch.trim().toLowerCase();
  const filteredItems = searchLower
    ? menuItems.filter(i => i.name.toLowerCase().includes(searchLower))
    : menuItems;
  const filteredCombos = searchLower
    ? combos.filter(c => c.name.toLowerCase().includes(searchLower))
    : combos;

  const handleConfirmServe = async () => {
    if (!servingStudent || selectedItems.length === 0) return;
    setSubmitting(true);
    setError('');
    try {
      const res = await mealsAPI.serve(servingStudent.id, selectedItems);
      setLastServed(res.data);
      setServingStudent(null);
      setSelectedItems([]);
      runSearch(query);
    } catch (e) {
      setError(e.response?.data?.error || 'Could not record meal.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={styles.page}>
      <Topbar
        title="Serve Meals"
        subtitle="Search a student, pick what they took, and record it"
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
            {' '}{lastServed.items.join(', ')} — KES {lastServed.deducted_ksh.toFixed(2)} deducted,
            new balance KES {lastServed.new_balance_ksh.toFixed(2)}
            {' '}(served by {lastServed.served_by})
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
                    {s.credit_limit_ksh > 0 && (
                      <span style={styles.creditNote}>
                        {' '}(+KES {s.credit_limit_ksh.toFixed(2)} credit)
                      </span>
                    )}
                  </td>
                  <td style={styles.td}>
                    {s.already_served_today ? (
                      <span style={styles.badgeServed}>Already served</span>
                    ) : (
                      <span style={styles.badgeOk}>Eligible</span>
                    )}
                  </td>
                  <td style={styles.td}>
                    <button
                      style={{
                        ...styles.serveBtn,
                        ...(!s.eligible ? styles.serveBtnDisabled : {})
                      }}
                      disabled={!s.eligible}
                      onClick={() => openServeModal(s)}
                    >
                      Serve Meal
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {servingStudent && (
        <div style={styles.modalOverlay} onClick={() => setServingStudent(null)}>
          <div style={styles.modal} onClick={e => e.stopPropagation()}>
            <h3 style={styles.modalTitle}>Serve {servingStudent.full_name}</h3>
            <p style={styles.modalSub}>Search a meal or a meal combination, or pick items below</p>

            <input
              style={styles.itemSearch}
              placeholder="Search food or combination (e.g. 'Lunch Special')..."
              value={itemSearch}
              onChange={e => setItemSearch(e.target.value)}
              autoFocus
            />

            {filteredCombos.length > 0 && (
              <div style={styles.comboSection}>
                <p style={styles.comboSectionLabel}>Meal Combinations</p>
                {filteredCombos.map(combo => (
                  <button
                    key={combo.id}
                    type="button"
                    style={styles.comboBtn}
                    onClick={() => addCombo(combo)}
                  >
                    <span style={styles.comboBtnName}>{combo.name}</span>
                    <span style={styles.comboBtnSub}>
                      {combo.items.map(i => i.name).join(', ')}
                    </span>
                    <span style={styles.comboBtnPrice}>
                      KES {combo.total_price_ksh.toFixed(2)}
                    </span>
                  </button>
                ))}
              </div>
            )}

            {menuItems.length === 0 ? (
              <p style={styles.empty}>No menu items configured yet.</p>
            ) : filteredItems.length === 0 ? (
              <p style={styles.empty}>No matching items.</p>
            ) : (
              <div style={styles.itemList}>
                {filteredItems.map(item => (
                  <label key={item.id} style={styles.itemRow}>
                    <input
                      type="checkbox"
                      checked={selectedItems.includes(item.id)}
                      onChange={() => toggleItem(item.id)}
                    />
                    <span style={styles.itemName}>{item.name}</span>
                    <span style={styles.itemPrice}>
                      KES {item.price_ksh.toFixed(2)}
                    </span>
                  </label>
                ))}
              </div>
            )}

            <div style={styles.totalRow}>
              <span>Total</span>
              <strong>KES {(totalCents / 100).toFixed(2)}</strong>
            </div>

            {error && <div style={styles.errorBanner}>{error}</div>}

            <div style={styles.modalActions}>
              <button style={styles.cancelBtn} onClick={() => setServingStudent(null)}>
                Cancel
              </button>
              <button
                style={{
                  ...styles.confirmBtn,
                  ...(selectedItems.length === 0 || submitting ? styles.serveBtnDisabled : {})
                }}
                disabled={selectedItems.length === 0 || submitting}
                onClick={handleConfirmServe}
              >
                {submitting ? 'Recording...' : 'Confirm & Record'}
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
  creditNote: { fontSize: 11, fontWeight: 500, color: '#6B9AB8' },
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
  modalOverlay: { position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                  background: 'rgba(0,0,0,0.4)', display: 'flex',
                  alignItems: 'center', justifyContent: 'center', zIndex: 100 },
  modal: { background: '#fff', borderRadius: 12, padding: 28, width: 420,
           maxHeight: '80vh', overflow: 'auto',
           boxShadow: '0 8px 32px rgba(0,0,0,0.2)' },
  modalTitle: { margin: 0, fontSize: 18, fontWeight: 700, color: '#1A3A5C' },
  modalSub: { margin: '4px 0 16px', fontSize: 13, color: '#6B7280' },
  itemSearch: { width: '100%', border: '1px solid #E5E7EB', borderRadius: 8,
                padding: '10px 14px', fontSize: 13, outline: 'none',
                boxSizing: 'border-box', marginBottom: 14 },
  comboSection: { marginBottom: 14 },
  comboSectionLabel: { fontSize: 11, fontWeight: 700, color: '#6B9AB8',
                       textTransform: 'uppercase', letterSpacing: 0.4,
                       margin: '0 0 8px' },
  comboBtn: { display: 'flex', flexDirection: 'column', alignItems: 'flex-start',
              width: '100%', background: '#EEF0FB', border: '1px solid #C7CDF0',
              borderRadius: 8, padding: '10px 12px', marginBottom: 6,
              cursor: 'pointer', textAlign: 'left' },
  comboBtnName: { fontSize: 13, fontWeight: 700, color: '#3A4AB0' },
  comboBtnSub: { fontSize: 11, color: '#6B7280', marginTop: 2 },
  comboBtnPrice: { fontSize: 12, fontWeight: 700, color: '#1A3A5C', marginTop: 4 },
  itemList: { display: 'flex', flexDirection: 'column', gap: 2 },
  itemRow: { display: 'flex', alignItems: 'center', gap: 10,
             padding: '10px 8px', borderBottom: '1px solid #F3F4F6',
             cursor: 'pointer', fontSize: 14 },
  itemName: { flex: 1, color: '#374151' },
  itemPrice: { color: '#1A3A5C', fontWeight: 600, fontSize: 13 },
  totalRow: { display: 'flex', justifyContent: 'space-between',
              padding: '16px 8px 0', fontSize: 15, color: '#1A3A5C' },
  modalActions: { display: 'flex', gap: 10, marginTop: 20 },
  cancelBtn: { flex: 1, background: '#F3F4F6', color: '#374151', border: 'none',
               borderRadius: 8, padding: '10px 16px', fontSize: 13,
               fontWeight: 600, cursor: 'pointer' },
  confirmBtn: { flex: 1, background: '#1A6E3C', color: '#fff', border: 'none',
                borderRadius: 8, padding: '10px 16px', fontSize: 13,
                fontWeight: 600, cursor: 'pointer' },
};
