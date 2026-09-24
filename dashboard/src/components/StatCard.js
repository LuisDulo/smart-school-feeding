import React from 'react';

export default function StatCard({ icon: Icon, value, label, color, loading }) {
  return (
    <div style={{ ...styles.card, borderTop: `4px solid ${color}` }}>
      <div style={styles.row}>
        <Icon style={{ ...styles.icon, color }} />
        <span style={{ ...styles.value, color }}>
          {loading ? '—' : value}
        </span>
      </div>
      <p style={styles.label}>{label}</p>
    </div>
  );
}

const styles = {
  card: { background: '#fff', borderRadius: 12, padding: '20px 24px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.05)', flex: 1 },
  row: { display: 'flex', alignItems: 'center',
         justifyContent: 'space-between', marginBottom: 8 },
  icon: { width: 24, height: 24 },
  value: { fontSize: 28, fontWeight: 700 },
  label: { margin: 0, fontSize: 12, color: '#6B7280' },
};
