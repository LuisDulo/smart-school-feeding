import React from 'react';
import {
  FiHome, FiUsers, FiTrendingUp, FiAlertTriangle,
  FiClipboard, FiLogOut
} from 'react-icons/fi';
import { MdOutlineRestaurant, MdOutlineSchool, MdOutlineRoomService } from 'react-icons/md';
import { useAuth } from '../context/AuthContext';

const NAV_ITEMS = [
  { key: 'dashboard',  label: 'Dashboard',        Icon: FiHome },
  { key: 'balances',   label: 'Student Balances',  Icon: FiUsers },
  { key: 'serve',      label: 'Serve Meals',       Icon: MdOutlineRoomService },
  { key: 'meals',      label: 'Meal Distribution', Icon: MdOutlineRestaurant },
  { key: 'forecast',   label: 'Demand Forecast',   Icon: FiTrendingUp },
  { key: 'anomalies',  label: 'Anomaly Flags',     Icon: FiAlertTriangle },
  { key: 'reports',    label: 'Reports',           Icon: FiClipboard },
];

export default function Sidebar({ active, onNavigate, flagCount = 0 }) {
  const { user, logout } = useAuth();

  return (
    <div style={styles.sidebar}>
      <div style={styles.brand}>
        <p style={styles.brandTitle}>School Feeding</p>
        <p style={styles.brandSub}>Management System</p>
      </div>

      <div style={styles.school}>
        <p style={styles.schoolName}>
          <MdOutlineSchool style={styles.inlineIcon} />
          {user?.school?.name || 'School'}
        </p>
        <p style={styles.schoolRole}>{user?.role} · {user?.full_name}</p>
      </div>

      {NAV_ITEMS.map(item => (
        <div
          key={item.key}
          style={{
            ...styles.navItem,
            ...(active === item.key ? styles.navItemActive : {})
          }}
          onClick={() => onNavigate(item.key)}
        >
          <item.Icon style={styles.navIcon} />
          <span>{item.label}</span>
          {item.key === 'anomalies' && flagCount > 0 && (
            <span style={styles.badge}>{flagCount}</span>
          )}
        </div>
      ))}

      <div style={styles.logout} onClick={logout}>
        <FiLogOut style={styles.inlineIcon} /> Logout
      </div>
    </div>
  );
}

const styles = {
  sidebar: { width: 220, background: '#1A3A5C', height: '100vh',
             display: 'flex', flexDirection: 'column', flexShrink: 0 },
  brand: { padding: '24px 20px 16px', borderBottom: '1px solid #2A4A6C' },
  brandTitle: { color: '#fff', fontWeight: 700, fontSize: 14, margin: 0 },
  brandSub: { color: '#6B9AB8', fontSize: 11, margin: '4px 0 0' },
  school: { padding: '12px 20px 16px', borderBottom: '1px solid #2A4A6C' },
  schoolName: { color: '#A8D8C0', fontSize: 12, fontWeight: 600, margin: 0 },
  schoolRole: { color: '#6B9AB8', fontSize: 11, margin: '4px 0 0' },
  navItem: { display: 'flex', alignItems: 'center', gap: 10,
             padding: '12px 20px', color: '#A8BCC8', fontSize: 13,
             cursor: 'pointer', transition: 'all 0.15s' },
  navItemActive: { background: '#1A6E3C', color: '#fff', fontWeight: 600 },
  navIcon: { width: 17, height: 17, flexShrink: 0 },
  inlineIcon: { width: 14, height: 14, verticalAlign: -2, marginRight: 6 },
  badge: { marginLeft: 'auto', background: '#C0392B', color: '#fff',
           fontSize: 10, fontWeight: 700, borderRadius: 10,
           padding: '2px 7px' },
  logout: { marginTop: 'auto', padding: '16px 20px',
            color: '#6B9AB8', fontSize: 13, cursor: 'pointer',
            borderTop: '1px solid #2A4A6C', display: 'flex',
            alignItems: 'center' },
};
