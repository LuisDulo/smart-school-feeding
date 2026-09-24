import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Alert } from 'react-native';
import { useAuth } from '../context/AuthContext';

export default function HomeScreen() {
  const { user, logout } = useAuth();

  const handleLogout = () => {
    Alert.alert('Log out', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Log out', style: 'destructive', onPress: logout }
    ]);
  };

  const balanceKsh = user?.balance_cents ? (user.balance_cents / 100).toFixed(2) : '0.00';

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.greeting}>Good morning 👋</Text>
        <Text style={styles.name}>{user?.full_name}</Text>
        <Text style={styles.role}>{user?.school?.name} · {user?.role}</Text>
      </View>

      {user?.role === 'student' && (
        <View style={styles.balanceCard}>
          <Text style={styles.balanceLabel}>Meal Account Balance</Text>
          <Text style={styles.balanceAmount}>KES {balanceKsh}</Text>
          <Text style={styles.balanceSub}>Sprint 3 — Top Up coming soon</Text>
        </View>
      )}

      <View style={styles.placeholders}>
        <Text style={styles.placeholderTitle}>Coming in Sprint 3 →</Text>
        <Text style={styles.placeholderItem}>💳  Top Up via M-Pesa</Text>
        <Text style={styles.placeholderItem}>📋  Payment History</Text>
        <Text style={styles.placeholderItem}>🔔  Low Balance Alerts</Text>
      </View>

      <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
        <Text style={styles.logoutText}>Log out</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F7F9FC' },
  header: { backgroundColor: '#1A3A5C', padding: 28, paddingTop: 60 },
  greeting: { color: '#A8D8C0', fontSize: 14 },
  name: { color: '#fff', fontSize: 22, fontWeight: '700', marginTop: 4 },
  role: { color: '#6B9AB8', fontSize: 12, marginTop: 4 },
  balanceCard: { margin: 20, backgroundColor: '#fff', borderRadius: 16,
                 padding: 24, shadowColor: '#000', shadowOpacity: 0.06,
                 shadowRadius: 12, elevation: 3, alignItems: 'center' },
  balanceLabel: { fontSize: 13, color: '#6B7280', marginBottom: 8 },
  balanceAmount: { fontSize: 36, fontWeight: '700', color: '#1A3A5C' },
  balanceSub: { fontSize: 11, color: '#9CA3AF', marginTop: 8 },
  placeholders: { margin: 20, backgroundColor: '#fff', borderRadius: 16, padding: 20 },
  placeholderTitle: { fontSize: 13, fontWeight: '700', color: '#1A6E3C', marginBottom: 12 },
  placeholderItem: { fontSize: 14, color: '#6B7280', marginBottom: 10 },
  logoutBtn: { margin: 20, borderWidth: 1, borderColor: '#E5E7EB',
               borderRadius: 10, padding: 14, alignItems: 'center' },
  logoutText: { color: '#EF4444', fontWeight: '600', fontSize: 14 },
});
