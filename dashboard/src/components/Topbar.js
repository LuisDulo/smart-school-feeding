import React from 'react';

export default function Topbar({ title, subtitle }) {
  return (
    <div style={styles.topbar}>
      <div>
        <h1 style={styles.title}>{title}</h1>
        {subtitle && <p style={styles.subtitle}>{subtitle}</p>}
      </div>
    </div>
  );
}

const styles = {
  topbar: { background: '#fff', padding: '16px 32px',
            borderBottom: '1px solid #E5E7EB',
            display: 'flex', alignItems: 'center',
            justifyContent: 'space-between' },
  title: { margin: 0, fontSize: 20, fontWeight: 700, color: '#1A3A5C' },
  subtitle: { margin: '4px 0 0', fontSize: 12, color: '#6B7280' },
};
