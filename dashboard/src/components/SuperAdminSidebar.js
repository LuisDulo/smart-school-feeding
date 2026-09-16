import React from 'react';
import { useAuth } from '../context/AuthContext';

const NAV = [
  { key: 'overview',   label: 'Overview',         icon: '🌐' },
  { key: 'schools',    label: 'Schools',           icon: '🏫' },
  { key: 'analytics',  label: 'Analytics',         icon: '📊' },
  { key: 'students',   label: 'All Students',      icon: '👥' },
  { key: 'staff',      label: 'Staff Management',  icon: '👤' },
  { key: 'anomalies',  label: 'Anomaly Flags',     icon: '🚨' },
  { key: 'reports',    label: 'Network Reports',   icon: '📋' },
];

export default function SuperAdminSidebar({
  active, onNavigate, flagCount = 0 }) {
  const { logout } = useAuth();

  return (
    <div style={styles.sidebar}>
      <div style={styles.brand}>
        <p style={styles.brandTitle}>Webmasters Kenya</p>
        <p style={styles.brandSub}>Super Admin Portal</p>
      </div>

      <div style={styles.badge}>
        🔑 SUPERADMIN ACCESS
      </div>

      {NAV.map(item => (
        <div
          key={item.key}
          style={{
            ...styles.navItem,
            ...(active === item.key ? styles.navActive : {})
          }}
          onClick={() => onNavigate(item.key)}
        >
          <span style={styles.navIcon}>{item.icon}</span>
          <span>{item.label}</span>
          {item.key === 'anomalies' && flagCount > 0 && (
            <span style={styles.flagBadge}>{flagCount}</span>
          )}
        </div>
      ))}

      <div style={styles.logout} onClick={logout}>
        ← Logout
      </div>
    </div>
  );
}

const styles = {
  sidebar: { width: 230, background: '#0F2035',
             height: '100vh', display: 'flex',
             flexDirection: 'column', flexShrink: 0 },
  brand: { padding: '24px 20px 12px',
           borderBottom: '1px solid #1A3A5C' },
  brandTitle: { color: '#fff', fontWeight: 700,
                fontSize: 14, margin: 0 },
  brandSub: { color: '#4A7A9B', fontSize: 11,
              margin: '4px 0 0' },
  badge: { margin: '12px 16px',
           background: '#1A6E3C', color: '#fff',
           fontSize: 10, fontWeight: 700, padding: '6px 12px',
           borderRadius: 6, textAlign: 'center',
           letterSpacing: 1 },
  navItem: { display: 'flex', alignItems: 'center',
             gap: 10, padding: '12px 20px',
             color: '#8AAFC4', fontSize: 13,
             cursor: 'pointer' },
  navActive: { background: '#1A6E3C',
               color: '#fff', fontWeight: 700 },
  navIcon: { fontSize: 16 },
  flagBadge: { marginLeft: 'auto', background: '#C0392B',
               color: '#fff', fontSize: 10, fontWeight: 700,
               borderRadius: 10, padding: '2px 7px' },
  logout: { marginTop: 'auto', padding: '16px 20px',
            color: '#4A7A9B', fontSize: 13,
            cursor: 'pointer',
            borderTop: '1px solid #1A3A5C' },
};
