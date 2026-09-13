import React, { useState } from 'react';
import { authAPI } from '../services/api';

export default function Login({ onLogin }) {
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
      const { tokens, user } = res.data;
      localStorage.setItem('access_token', tokens.access);
      localStorage.setItem('refresh_token', tokens.refresh);
      localStorage.setItem('user_data', JSON.stringify(user));
      onLogin(user);
    } catch (err) {
      setError(err.response?.data?.error || 'Login failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.page}>
      <div style={styles.left}>
        <h1 style={styles.brand}>Smart School<br/>Feeding System</h1>
        <p style={styles.brandSub}>Administrative Dashboard</p>
        <p style={styles.brandSub}>Partner: Webmasters Kenya</p>
        {['M-Pesa Integration', 'Demand Forecasting', 'Anomaly Detection'].map(f => (
          <p key={f} style={styles.feature}>✓  {f}</p>
        ))}
      </div>

      <div style={styles.right}>
        <div style={styles.card}>
          <h2 style={styles.cardTitle}>Administrator Sign In</h2>
          <p style={styles.cardSub}>Dashboard access for school staff</p>

          <form onSubmit={handleSubmit}>
            <label style={styles.label}>Email address</label>
            <input
              style={styles.input}
              type="email"
              placeholder="admin@school.co.ke"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
            />
            <label style={styles.label}>Password</label>
            <input
              style={styles.input}
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
            />
            {error && <p style={styles.error}>{error}</p>}
            <button style={styles.button} type="submit" disabled={loading}>
              {loading ? 'Signing in...' : 'Sign In to Dashboard'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

const styles = {
  page: { display: 'flex', height: '100vh', fontFamily: 'Inter, sans-serif' },
  left: { width: '40%', background: '#1A3A5C', padding: '60px 48px',
          display: 'flex', flexDirection: 'column', justifyContent: 'center' },
  brand: { color: '#fff', fontSize: 32, fontWeight: 700, lineHeight: 1.2, margin: 0 },
  brandSub: { color: '#6B9AB8', fontSize: 14, marginTop: 8 },
  feature: { color: '#A8D8C0', fontSize: 14, marginTop: 12 },
  right: { flex: 1, background: '#F7F9FC', display: 'flex',
           alignItems: 'center', justifyContent: 'center' },
  card: { background: '#fff', borderRadius: 16, padding: 40, width: 400,
          boxShadow: '0 4px 24px rgba(0,0,0,0.06)' },
  cardTitle: { color: '#1A3A5C', fontSize: 22, fontWeight: 700, margin: '0 0 4px' },
  cardSub: { color: '#6B7280', fontSize: 13, marginBottom: 28 },
  label: { display: 'block', fontSize: 13, fontWeight: 600,
           color: '#374151', marginBottom: 6, marginTop: 16 },
  input: { width: '100%', border: '1px solid #E5E7EB', borderRadius: 8,
           padding: '12px 14px', fontSize: 14, boxSizing: 'border-box',
           outline: 'none', color: '#111827' },
  error: { color: '#EF4444', fontSize: 13, marginTop: 12 },
  button: { width: '100%', background: '#1A6E3C', color: '#fff', border: 'none',
            borderRadius: 8, padding: '14px', fontSize: 15, fontWeight: 700,
            marginTop: 24, cursor: 'pointer' },
};
