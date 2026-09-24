import React, { useState } from 'react';
import { FiCheck } from 'react-icons/fi';
import { AuthProvider, useAuth } from './context/AuthContext';
import { authAPI } from './services/api';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import StudentBalances from './pages/StudentBalances';
import ServeMeals from './pages/ServeMeals';
import MealDistribution from './pages/MealDistribution';
import ForecastPage from './pages/ForecastPage';
import AnomalyFlags from './pages/AnomalyFlags';
import Reports from './pages/Reports';
import MenuManagement from './pages/MenuManagement';
import AccountManagement from './pages/AccountManagement';
import CreditRequests from './pages/CreditRequests';
import SupportIssues from './pages/SupportIssues';
import PlatformSupport from './pages/PlatformSupport';
import SuperAdminSidebar from './components/SuperAdminSidebar';
import SAOverview from './pages/superadmin/SAOverview';
import SASchools from './pages/superadmin/SASchools';
import SAAnalytics from './pages/superadmin/SAAnalytics';
import SAReports from './pages/superadmin/SAReports';
import SAStudents from './pages/superadmin/SAStudents';
import SAStaff from './pages/superadmin/SAStaff';
import SAAnomalies from './pages/superadmin/SAAnomalies';
import SAAdminIssues from './pages/superadmin/SAAdminIssues';
import SASchoolDrillDown from './pages/superadmin/SASchoolDrillDown';

function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await authAPI.login({ email, password });
      login(res.data.user, res.data.tokens);
    } catch (err) {
      setError(err.response?.data?.error || 'Login failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={loginStyles.page}>
      <div style={loginStyles.left}>
        <h1 style={loginStyles.brand}>Smart School<br />Feeding System</h1>
        <p style={loginStyles.sub}>Administrative Dashboard</p>
        <p style={loginStyles.sub}>Partner: Webmasters Kenya</p>
        {['M-Pesa Integration', 'Linear Regression Forecasting',
          'Isolation Forest Anomaly Detection'].map(f => (
          <p key={f} style={loginStyles.feature}>
            <FiCheck style={loginStyles.featureIcon} /> {f}
          </p>
        ))}
      </div>
      <div style={loginStyles.right}>
        <div style={loginStyles.card}>
          <h2 style={loginStyles.cardTitle}>Administrator Sign In</h2>
          <form onSubmit={handleSubmit}>
            <label style={loginStyles.label}>Email</label>
            <input style={loginStyles.input} type="email"
              placeholder="admin@school.co.ke"
              value={email} onChange={e => setEmail(e.target.value)}
              required />
            <label style={loginStyles.label}>Password</label>
            <input style={loginStyles.input} type="password"
              placeholder="••••••••"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required />
            {error && <p style={loginStyles.error}>{error}</p>}
            <button style={loginStyles.btn} type="submit" disabled={loading}>
              {loading ? 'Signing in...' : 'Sign In to Dashboard'}
            </button>
          </form>
          <p style={{ fontSize: 11, color: '#9CA3AF', marginTop: 16 }}>
            Test: admin@strathmoreprimary.ac.ke / Admin123!
          </p>
        </div>
      </div>
    </div>
  );
}

const PAGES = {
  dashboard: Dashboard,
  balances: StudentBalances,
  serve: ServeMeals,
  menu: MenuManagement,
  meals: MealDistribution,
  accounts: AccountManagement,
  credit: CreditRequests,
  issues: SupportIssues,
  forecast: ForecastPage,
  anomalies: AnomalyFlags,
  reports: Reports,
  platformSupport: PlatformSupport,
};

function AppInner() {
  const { user } = useAuth();
  const [page, setPage] = useState('dashboard');

  // Super admin state
  const [saPage, setSaPage] = useState('overview');
  const [drillDownSchool, setDrillDownSchool] = useState(null);

  if (!user) return <LoginPage />;

  // Super admin gets a completely separate layout — a different sidebar,
  // network-wide pages, and no access to any single school's admin pages.
  if (user.role === 'superadmin') {
    const handleDrillDown = (schoolId, schoolName) => {
      setDrillDownSchool({ id: schoolId, name: schoolName });
      setSaPage('drilldown');
    };
    const handleBack = () => {
      setDrillDownSchool(null);
      setSaPage('overview');
    };

    const renderSAPage = () => {
      switch (saPage) {
        case 'overview':
          return <SAOverview onDrillDown={handleDrillDown} />;
        case 'schools':
          return <SASchools onDrillDown={handleDrillDown} />;
        case 'analytics':
          return <SAAnalytics />;
        case 'students':
          return <SAStudents />;
        case 'staff':
          return <SAStaff />;
        case 'anomalies':
          return <SAAnomalies />;
        case 'schoolReports':
          return <SAAdminIssues />;
        case 'reports':
          return <SAReports />;
        case 'drilldown':
          return drillDownSchool
            ? <SASchoolDrillDown
                schoolId={drillDownSchool.id}
                schoolName={drillDownSchool.name}
                onBack={handleBack} />
            : <SAOverview onDrillDown={handleDrillDown} />;
        default:
          return <SAOverview onDrillDown={handleDrillDown} />;
      }
    };

    return (
      <div style={{ display: 'flex', height: '100vh',
                    fontFamily: 'Inter, sans-serif' }}>
        <SuperAdminSidebar
          active={saPage}
          onNavigate={setSaPage}
        />
        <div style={{ flex: 1, overflow: 'auto' }}>
          {renderSAPage()}
        </div>
      </div>
    );
  }

  // Regular school users — existing layout
  const PageComponent = PAGES[page] || Dashboard;
  return (
    <div style={{ display: 'flex', height: '100vh',
                  fontFamily: 'Inter, sans-serif' }}>
      <Sidebar active={page} onNavigate={setPage} />
      <div style={{ flex: 1, overflow: 'auto' }}>
        <PageComponent />
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppInner />
    </AuthProvider>
  );
}

const loginStyles = {
  page: { display: 'flex', height: '100vh',
          fontFamily: 'Inter, sans-serif' },
  left: { width: '40%', background: '#1A3A5C', padding: '60px 48px',
          display: 'flex', flexDirection: 'column',
          justifyContent: 'center' },
  brand: { color: '#fff', fontSize: 32, fontWeight: 700,
           lineHeight: 1.2, margin: 0 },
  sub: { color: '#6B9AB8', fontSize: 14, marginTop: 8 },
  feature: { color: '#A8D8C0', fontSize: 14, marginTop: 12,
             display: 'flex', alignItems: 'center', gap: 8 },
  featureIcon: { width: 15, height: 15, flexShrink: 0 },
  right: { flex: 1, background: '#F7F9FC', display: 'flex',
           alignItems: 'center', justifyContent: 'center' },
  card: { background: '#fff', borderRadius: 16, padding: 40,
          width: 400, boxShadow: '0 4px 24px rgba(0,0,0,0.06)' },
  cardTitle: { color: '#1A3A5C', fontSize: 22,
               fontWeight: 700, margin: '0 0 24px' },
  label: { display: 'block', fontSize: 13, fontWeight: 600,
           color: '#374151', marginBottom: 6, marginTop: 16 },
  input: { width: '100%', border: '1px solid #E5E7EB', borderRadius: 8,
           padding: '12px 14px', fontSize: 14, boxSizing: 'border-box',
           outline: 'none' },
  error: { color: '#EF4444', fontSize: 13, marginTop: 12 },
  btn: { width: '100%', background: '#1A6E3C', color: '#fff',
         border: 'none', borderRadius: 8, padding: 14,
         fontSize: 15, fontWeight: 700, marginTop: 24,
         cursor: 'pointer' },
};
