import React, { useState, useEffect } from 'react';
import Login from './pages/Login';
import DashboardHome from './pages/DashboardHome';

export default function App() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    const stored = localStorage.getItem('user_data');
    const token = localStorage.getItem('access_token');
    if (stored && token) setUser(JSON.parse(stored));
  }, []);

  const handleLogin = (userData) => setUser(userData);

  const handleLogout = () => {
    localStorage.clear();
    setUser(null);
  };

  return user
    ? <DashboardHome user={user} onLogout={handleLogout} />
    : <Login onLogin={handleLogin} />;
}
