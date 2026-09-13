import React from 'react';

export default function DashboardHome({ user, onLogout }) {
  return (
    <div style={styles.page}>
      <div style={styles.sidebar}>
        <div style={styles.sidebarHeader}>
          <p style={styles.sidebarTitle}>School Feeding</p>
          <p style={styles.sidebarSub}>Management System</p>
        </div>
        {['Dashboard','Student Balances','Meal Distribution',
          'Demand Forecast','Anomaly Flags','Reports'].map((item, i) => (
          <div key={item} style={{...styles.navItem, ...(i===0 ? styles.navItemActive : {})}}>
            {item}
          </div>
        ))}
        <div style={styles.navItem} onClick={onLogout}>← Logout</div>
      </div>

      <div style={styles.main}>
        <div style={styles.topbar}>
          <div>
            <h1 style={styles.pageTitle}>Dashboard</h1>
            <p style={styles.pageSub}>Welcome back, {user?.full_name}</p>
          </div>
          <div style={styles.userChip}>{user?.role} · {user?.school?.name}</div>
        </div>

        <div style={styles.cards}>
          {[
            { label: 'Payments today', value: '—', color: '#1A6E3C' },
            { label: 'Meals served today', value: '—', color: '#3A4AB0' },
            { label: 'Low balance students', value: '—', color: '#D07020' },
            { label: 'Anomaly flags', value: '—', color: '#C0392B' },
          ].map(c => (
            <div key={c.label} style={{...styles.card, borderTop: `4px solid ${c.color}`}}>
              <p style={styles.cardValue}>{c.value}</p>
              <p style={styles.cardLabel}>{c.label}</p>
            </div>
          ))}
        </div>

        <div style={styles.placeholder}>
          <h3 style={{ color: '#1A6E3C', margin: '0 0 8px' }}>Sprint 3 onwards →</h3>
          <p style={{ color: '#6B7280', fontSize: 14 }}>
            M-Pesa payment data, meal distribution charts, demand forecasts,
            and anomaly flag queue will appear here once Sprint 3 and 4 are complete.
          </p>
        </div>
      </div>
    </div>
  );
}

const styles = {
  page: { display: 'flex', height: '100vh', fontFamily: 'Inter, sans-serif' },
  sidebar: { width: 220, background: '#1A3A5C', padding: '24px 0', flexShrink: 0 },
  sidebarHeader: { padding: '0 20px 24px', borderBottom: '1px solid #2A4A6C' },
  sidebarTitle: { color: '#fff', fontWeight: 700, fontSize: 14, margin: 0 },
  sidebarSub: { color: '#6B9AB8', fontSize: 11, margin: '4px 0 0' },
  navItem: { padding: '12px 20px', color: '#A8BCC8', fontSize: 13,
             cursor: 'pointer', marginTop: 2 },
  navItemActive: { background: '#1A6E3C', color: '#fff', fontWeight: 600 },
  main: { flex: 1, background: '#F7F9FC', overflow: 'auto' },
  topbar: { background: '#fff', padding: '20px 32px', borderBottom: '1px solid #E5E7EB',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  pageTitle: { margin: 0, fontSize: 22, fontWeight: 700, color: '#1A3A5C' },
  pageSub: { margin: '4px 0 0', fontSize: 13, color: '#6B7280' },
  userChip: { background: '#F0F4F8', padding: '8px 16px', borderRadius: 20,
              fontSize: 12, color: '#374151' },
  cards: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
           gap: 20, padding: 32 },
  card: { background: '#fff', borderRadius: 12, padding: 20,
          boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
  cardValue: { fontSize: 28, fontWeight: 700, color: '#1A3A5C', margin: '0 0 4px' },
  cardLabel: { fontSize: 12, color: '#6B7280', margin: 0 },
  placeholder: { margin: '0 32px', background: '#fff', borderRadius: 12,
                 padding: 24, boxShadow: '0 2px 8px rgba(0,0,0,0.04)' },
};
