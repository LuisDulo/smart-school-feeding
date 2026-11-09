import React, { createContext, useState, useContext, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { authAPI, setOnSessionExpired } from '../services/api';
import { registerForPush, unregisterPush } from '../services/pushNotifications';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkStoredToken();
    // The API client calls this when the refresh token is rejected.
    setOnSessionExpired(async () => {
      await AsyncStorage.multiRemove(['access_token', 'refresh_token', 'user_data']);
      setUser(null);
    });
  }, []);

  const checkStoredToken = async () => {
    try {
      const token = await AsyncStorage.getItem('access_token');
      const userData = await AsyncStorage.getItem('user_data');
      if (token && userData) {
        const stored = JSON.parse(userData);
        setUser(stored);
        if (stored.role !== 'kitchen') registerForPush(); // refresh token on each launch
      }
    } catch (e) {
      console.log('No stored session');
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    const response = await authAPI.login({ email, password });
    const { tokens, user } = response.data;
    await AsyncStorage.setItem('access_token', tokens.access);
    await AsyncStorage.setItem('refresh_token', tokens.refresh);
    await AsyncStorage.setItem('user_data', JSON.stringify(user));
    setUser(user);
    if (user.role !== 'kitchen') registerForPush();
    return user;
  };

  const register = async (data) => {
    const response = await authAPI.register(data);
    const { tokens, user } = response.data;
    await AsyncStorage.setItem('access_token', tokens.access);
    await AsyncStorage.setItem('refresh_token', tokens.refresh);
    await AsyncStorage.setItem('user_data', JSON.stringify(user));
    setUser(user);
    if (user.role !== 'kitchen') registerForPush();
    return user;
  };

  const logout = async () => {
    // Needs the access token, so before storage is cleared; capped so an
    // offline phone can still log out promptly.
    await Promise.race([unregisterPush(), new Promise(r => setTimeout(r, 3000))]);
    try {
      const refresh = await AsyncStorage.getItem('refresh_token');
      if (refresh) await authAPI.logout(refresh); // awaited before storage is cleared
    } catch (e) {
      // Offline or token already invalid — still log out locally.
    }
    await AsyncStorage.multiRemove(['access_token', 'refresh_token', 'user_data']);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
