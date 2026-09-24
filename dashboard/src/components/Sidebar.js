import React from 'react';
import {
  FiHome, FiUsers, FiTrendingUp, FiAlertTriangle,
  FiClipboard, FiLogOut, FiUserPlus, FiCreditCard, FiHelpCircle
} from 'react-icons/fi';
import { MdOutlineRestaurant, MdOutlineSchool, MdOutlineRoomService, MdOutlineMenuBook } from 'react-icons/md';
import { useAuth } from '../context/AuthContext';

// `roles` mirrors each page's actual backend permission (see the
// corresponding view's permission_classes) so a role never sees a nav
// item that just 403s or silently shows nothing when clicked:
//  - balances/credit/issues/anomalies/reports -> IsAdminOrBursar
//  - serve                                    -> IsKitchenStaff
//  - menu/accounts                            -> IsSchoolAdmin (write);
//    kept out of kitchen/bursar nav since there's nothing for them to do there
//  - dashboard/meals/forecast                 -> IsAuthenticated (everyone)
const NAV_ITEMS = [
  { key: 'dashboard',  label: 'Dashboard',        Icon: FiHome,               roles: ['admin', 'bursar', 'kitchen'] },
  { key: 'balances',   label: 'Student Balances',  Icon: FiUsers,              roles: ['admin', 'bursar'] },
  { key: 'serve',      label: 'Serve Meals',       Icon: MdOutlineRoomService, roles: ['kitchen'] },
  { key: 'menu',       label: 'Menu Management',   Icon: MdOutlineMenuBook,    roles: ['admin'] },
  { key: 'meals',      label: 'Meal Distribution', Icon: MdOutlineRestaurant,  roles: ['admin', 'bursar', 'kitchen'] },
  { key: 'accounts',   label: 'Account Management', Icon: FiUserPlus,          roles: ['admin'] },
  { key: 'credit',     label: 'Credit Requests',   Icon: FiCreditCard,         roles: ['admin', 'bursar'] },
  { key: 'issues',     label: 'Support Issues',    Icon: FiHelpCircle,         roles: ['admin', 'bursar'] },
  { key: 'forecast',   label: 'Demand Forecast',   Icon: FiTrendingUp,         roles: ['admin', 'bursar', 'kitchen'] },
  { key: 'anomalies',  label: 'Anomaly Flags',     Icon: FiAlertTriangle,      roles: ['admin', 'bursar'] },
  { key: 'reports',    label: 'Reports',           Icon: FiClipboard,         roles: ['admin', 'bursar'] },
];

export default function Sidebar({ active, onNavigate, flagCount = 0 }) {
  const { user, logout } = useAuth();
  const visibleItems = NAV_ITEMS.filter(item => item.roles.includes(user?.role));

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

      {visibleItems.map(item => (
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
