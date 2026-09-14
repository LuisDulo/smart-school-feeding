import React, { useState, useEffect } from 'react';
import { FiPlus, FiTrash2 } from 'react-icons/fi';
import Topbar from '../components/Topbar';
import { mealsAPI } from '../services/api';

const TABS = [
  { key: 'items', label: 'Menu Items' },
  { key: 'combos', label: 'Meal Combinations' },
];

export default function MenuManagement() {
  const [tab, setTab] = useState('items');
  const [items, setItems] = useState([]);
  const [combos, setCombos] = useState([]);
  const [error, setError] = useState('');

  const loadItems = () => mealsAPI.menuList().then(res => setItems(res.data)).catch(() => setError('Could not load menu items.'));
  const loadCombos = () => mealsAPI.comboList().then(res => setCombos(res.data)).catch(() => setError('Could not load meal combinations.'));

  useEffect(() => { loadItems(); loadCombos(); }, []);

  return (
    <div style={styles.page}>
      <Topbar title="Menu Management" subtitle="Set food items and prices, and group common combinations kitchen staff can search for" />
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

        {tab === 'items' ? (
          <ItemsTab items={items} onChanged={loadItems} setError={setError} />
        ) : (
          <CombosTab items={items} combos={combos} onChanged={loadCombos} setError={setError} />
        )}
      </div>
    </div>
  );
}

function ItemsTab({ items, onChanged, setError }) {
  const [name, setName] = useState('');
  const [price, setPrice] = useState('');
  const [submitting, setSubmitting] = useState(false);

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
      onChanged();
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
      onChanged();
    } catch (e) {
      setError(e.response?.data?.error || 'Could not remove item.');
    }
  };

  return (
    <>
      <form style={styles.form} onSubmit={handleAdd}>
        <input
          style={styles.input}
          placeholder="Item name (e.g. Fries)"
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
            {items.length === 0 ? (
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
    </>
  );
}

function CombosTab({ items, combos, onChanged, setError }) {
  const [name, setName] = useState('');
  const [selectedItems, setSelectedItems] = useState([]);
  const [submitting, setSubmitting] = useState(false);

  const toggleItem = (id) => {
    setSelectedItems(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  };

  const previewTotal = selectedItems.reduce((sum, id) => {
    const item = items.find(i => i.id === id);
    return sum + (item ? item.price_cents : 0);
  }, 0);

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!name.trim() || selectedItems.length === 0) return;
    setSubmitting(true);
    setError('');
    try {
      await mealsAPI.comboCreate({ name: name.trim(), item_ids: selectedItems });
      setName('');
      setSelectedItems([]);
      onChanged();
    } catch (e) {
      setError(e.response?.data?.error || 'Could not create combination.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRemove = async (combo) => {
    if (!window.confirm(`Remove "${combo.name}" combination?`)) return;
    try {
      await mealsAPI.comboDelete(combo.id);
      onChanged();
    } catch (e) {
      setError(e.response?.data?.error || 'Could not remove combination.');
    }
  };

  return (
    <div style={styles.grid}>
      <form style={styles.card} onSubmit={handleAdd}>
        <h3 style={styles.cardTitle}>New Meal Combination</h3>
        <p style={styles.cardHint}>
          Group items into a named bundle (e.g. "Lunch Special") that kitchen
          staff can search for instead of picking each item individually.
          Its price always tracks the sum of the items below.
        </p>
        <label style={styles.label}>Name</label>
        <input
          style={styles.input}
          placeholder="e.g. Lunch Special"
          value={name}
          onChange={e => setName(e.target.value)}
        />
        <label style={styles.label}>Items in this combination</label>
        <div style={styles.checkList}>
          {items.length === 0 ? (
            <div style={styles.empty}>Add menu items first (Menu Items tab).</div>
          ) : items.map(item => (
            <label key={item.id} style={styles.checkRow}>
              <input
                type="checkbox"
                checked={selectedItems.includes(item.id)}
                onChange={() => toggleItem(item.id)}
              />
              <span style={{ flex: 1 }}>{item.name}</span>
              <span style={styles.checkPrice}>KES {item.price_ksh.toFixed(2)}</span>
            </label>
          ))}
        </div>
        <div style={styles.previewRow}>
          <span>Total price</span>
          <strong>KES {(previewTotal / 100).toFixed(2)}</strong>
        </div>
        <button style={styles.submitBtn} type="submit" disabled={submitting || selectedItems.length === 0}>
          {submitting ? 'Creating...' : 'Create Combination'}
        </button>
      </form>

      <div style={styles.listCard}>
        <h3 style={styles.cardTitle}>Combinations ({combos.length})</h3>
        <div style={styles.list}>
          {combos.length === 0 && <div style={styles.empty}>No combinations yet.</div>}
          {combos.map(combo => (
            <div key={combo.id} style={styles.comboRow}>
              <div style={styles.comboTop}>
                <div style={styles.comboName}>{combo.name}</div>
                <div style={styles.comboActions}>
                  <span style={styles.comboPrice}>KES {combo.total_price_ksh.toFixed(2)}</span>
                  <button style={styles.removeBtn} onClick={() => handleRemove(combo)}>
                    <FiTrash2 style={{ width: 14, height: 14 }} />
                  </button>
                </div>
              </div>
              <div style={styles.comboItems}>
                {combo.items.map(i => i.name).join(', ')}
              </div>
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
  content: { padding: 32 },
  tabs: { display: 'flex', gap: 4, marginBottom: 20,
          background: '#fff', borderRadius: 10, padding: 4, width: 'fit-content',
          boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  tab: { padding: '9px 18px', fontSize: 13, fontWeight: 600, color: '#6B7280',
         borderRadius: 8, cursor: 'pointer' },
  tabActive: { background: '#1A3A5C', color: '#fff' },
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
  grid: { display: 'grid', gridTemplateColumns: '380px 1fr', gap: 20 },
  card: { background: '#fff', borderRadius: 12, padding: 24,
          boxShadow: '0 2px 8px rgba(0,0,0,0.04)', height: 'fit-content' },
  cardTitle: { margin: '0 0 8px', fontSize: 15, fontWeight: 700, color: '#1A3A5C' },
  cardHint: { margin: '0 0 16px', fontSize: 12, color: '#6B7280', lineHeight: 1.5 },
  label: { display: 'block', fontSize: 12, fontWeight: 600, color: '#374151',
           marginBottom: 6, marginTop: 14 },
  checkList: { maxHeight: 220, overflow: 'auto', border: '1px solid #F3F4F6',
               borderRadius: 8, padding: 8 },
  checkRow: { display: 'flex', alignItems: 'center', gap: 8, padding: '8px 4px',
              fontSize: 13, color: '#374151', cursor: 'pointer' },
  checkPrice: { fontSize: 12, fontWeight: 600, color: '#1A3A5C' },
  previewRow: { display: 'flex', justifyContent: 'space-between',
                padding: '14px 4px 0', fontSize: 14, color: '#1A3A5C' },
  submitBtn: { width: '100%', background: '#1A6E3C', color: '#fff', border: 'none',
               borderRadius: 8, padding: '11px 16px', fontSize: 13,
               fontWeight: 700, marginTop: 18, cursor: 'pointer' },
  listCard: { background: '#fff', borderRadius: 12, padding: 24,
              boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  list: { display: 'flex', flexDirection: 'column', gap: 2, maxHeight: 480, overflow: 'auto' },
  comboRow: { padding: '12px 8px', borderBottom: '1px solid #F3F4F6' },
  comboTop: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  comboName: { fontSize: 14, fontWeight: 700, color: '#1A3A5C' },
  comboActions: { display: 'flex', alignItems: 'center', gap: 10 },
  comboPrice: { fontSize: 13, fontWeight: 700, color: '#1A6E3C' },
  comboItems: { fontSize: 12, color: '#6B7280', marginTop: 4 },
};
