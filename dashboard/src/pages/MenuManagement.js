import React, { useState, useEffect } from 'react';
import { FiPlus, FiTrash2 } from 'react-icons/fi';
import Topbar from '../components/Topbar';
import { mealsAPI } from '../services/api';

export default function MenuManagement() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [name, setName] = useState('');
  const [price, setPrice] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const load = () => {
    setLoading(true);
    mealsAPI.menuList()
      .then(res => setItems(res.data))
      .catch(() => setError('Could not load menu items.'))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!name.trim() || !price) return;
    setSubmitting(true);
    setError('');
    try {
      await mealsAPI.menuCreate({
        name: name.trim(),
        price_cents: Math.round(parseFloat(price) * 100),
      });
      setName('');
      setPrice('');
      load();
    } catch (e) {
      setError(e.response?.data?.error || 'Could not add item.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRemove = async (item) => {
    if (!window.confirm(`Remove "${item.name}" from the menu?`)) return;
    try {
      await mealsAPI.menuDelete(item.id);
      load();
    } catch (e) {
      setError(e.response?.data?.error || 'Could not remove item.');
    }
  };

  return (
    <div style={styles.page}>
      <Topbar title="Menu Management" subtitle="Set the food items and prices kitchen staff choose from when serving" />
      <div style={styles.content}>
        <form style={styles.form} onSubmit={handleAdd}>
          <input
            style={styles.input}
            placeholder="Item name (e.g. Rice)"
            value={name}
            onChange={e => setName(e.target.value)}
          />
          <input
            style={{ ...styles.input, width: 140 }}
            placeholder="Price (KES)"
            type="number"
            min="0.01"
            step="0.01"
            value={price}
            onChange={e => setPrice(e.target.value)}
          />
          <button style={styles.addBtn} disabled={submitting} type="submit">
            <FiPlus style={{ width: 14, height: 14 }} /> Add Item
          </button>
        </form>

        {error && <div style={styles.errorBanner}>{error}</div>}

        <div style={styles.tableWrap}>
          <table style={styles.table}>
            <thead>
              <tr style={styles.thead}>
                {['Item', 'Price (KES)', ''].map(h => (
                  <th key={h} style={styles.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={3} style={styles.empty}>Loading...</td></tr>
              ) : items.length === 0 ? (
                <tr><td colSpan={3} style={styles.empty}>No menu items yet — add one above.</td></tr>
              ) : items.map((item, i) => (
                <tr key={item.id} style={i % 2 === 0 ? styles.trEven : styles.trOdd}>
                  <td style={{ ...styles.td, fontWeight: 600 }}>{item.name}</td>
                  <td style={styles.td}>{item.price_ksh.toFixed(2)}</td>
                  <td style={styles.td}>
                    <button style={styles.removeBtn} onClick={() => handleRemove(item)}>
                      <FiTrash2 style={{ width: 14, height: 14 }} />
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
  form: { display: 'flex', gap: 10, marginBottom: 20 },
  input: { border: '1px solid #E5E7EB', borderRadius: 8,
           padding: '10px 14px', fontSize: 14, outline: 'none',
           boxSizing: 'border-box', flex: 1 },
  addBtn: { background: '#1A6E3C', color: '#fff', border: 'none',
            borderRadius: 8, padding: '10px 18px', fontSize: 13,
            fontWeight: 600, cursor: 'pointer', display: 'flex',
            alignItems: 'center', gap: 6, whiteSpace: 'nowrap' },
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
  removeBtn: { background: '#FEE2E2', color: '#C0392B', border: 'none',
               borderRadius: 8, padding: '6px 10px', cursor: 'pointer',
               display: 'flex', alignItems: 'center' },
};
