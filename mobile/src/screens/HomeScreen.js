import React, { useState, useCallback, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Alert } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { useAuth } from '../context/AuthContext';
import { paymentsAPI } from '../services/api';

const LOW_BALANCE_THRESHOLD_CENTS = 10000; // KES 100
// A parent has no meal_account of their own — the backend resolves
// /api/payments/balance/ and /history/ to their child's account instead
// (see resolve_meal_account in payments/views.py), so parents can see the
// same balance/history/low-balance UI as a student.
const CAN_VIEW_BALANCE = ['student', 'parent'];

export default function HomeScreen({ navigation }) {
  const { user, logout } = useAuth();
  const [balanceCents, setBalanceCents] = useState(
    user?.role === 'student' ? (user?.balance_cents ?? null) : null
  );
  // Whose balance this is — the logged-in student, or a parent's child.
  // Falls back to the logged-in user's own name until the first fetch
  // resolves (only matters for the brief instant before that response).
  const [studentName, setStudentName] = useState(user?.full_name ?? '');

  // Re-fetch the live balance every time Home comes into focus (e.g. after
  // returning from a confirmed top-up) — the balance on `user` is only a
  // snapshot from login/register (and only set for students at that) and
  // would otherwise go stale or simply be missing.
  useFocusEffect(
    useCallback(() => {
      if (!CAN_VIEW_BALANCE.includes(user?.role)) return;
      let cancelled = false;
      paymentsAPI.balance()
        .then(res => {
          if (cancelled) return;
          setBalanceCents(res.data.balance_cents);
          setStudentName(res.data.student_name);
        })
        .catch(() => {}); // keep last known balance on error
      return () => { cancelled = true; };
    }, [user?.role])
  );

  // Warn when the (live, not stale-snapshot) balance drops below the
  // low-balance threshold. Only re-fires when balanceCents actually
  // changes value, so dismissing the alert and returning to a still-low
  // balance doesn't re-trigger it every time Home refocuses.
  useEffect(() => {
    if (!CAN_VIEW_BALANCE.includes(user?.role)) return;
    if (balanceCents === null || balanceCents < 0) return;
    if (balanceCents >= LOW_BALANCE_THRESHOLD_CENTS) return;

    const timer = setTimeout(() => {
      navigation.navigate('LowBalanceAlert', {
        balance_ksh: balanceCents / 100,
        student_name: studentName
      });
    }, 1000);
    return () => clearTimeout(timer);
  }, [balanceCents, user, studentName]);

  const handleLogout = () => {
    Alert.alert('Log out', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Log out', style: 'destructive', onPress: logout }
    ]);
  };

  const balanceKsh = balanceCents != null ? (balanceCents / 100).toFixed(2) : '0.00';

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.greeting}>Good morning 👋</Text>
        <Text style={styles.name}>{user?.full_name}</Text>
        <Text style={styles.role}>{user?.school?.name} · {user?.role}</Text>
      </View>

      {CAN_VIEW_BALANCE.includes(user?.role) && (
        <View style={styles.balanceCard}>
          <Text style={styles.balanceLabel}>
            {user?.role === 'parent'
              ? `${studentName}'s Meal Balance`
              : 'Meal Account Balance'}
          </Text>
          <Text style={styles.balanceAmount}>KES {balanceKsh}</Text>
        </View>
      )}

      <View style={styles.actions}>
        <TouchableOpacity
          style={styles.actionBtn}
          onPress={() => navigation.navigate('TopUp')}
        >
          <Text style={styles.actionIcon}>💳</Text>
          <Text style={styles.actionLabel}>Top Up</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.actionBtn}
          onPress={() => navigation.navigate('PaymentHistory')}
        >
          <Text style={styles.actionIcon}>📋</Text>
          <Text style={styles.actionLabel}>History</Text>
        </TouchableOpacity>
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
  actions: { flexDirection: 'row', gap: 12, margin: 20 },
  actionBtn: { flex: 1, backgroundColor: '#fff', borderRadius: 12,
               padding: 20, alignItems: 'center',
               shadowColor: '#000', shadowOpacity: 0.04,
               shadowRadius: 6, elevation: 2 },
  actionIcon: { fontSize: 28, marginBottom: 8 },
  actionLabel: { fontSize: 13, fontWeight: '600', color: '#374151' },
  logoutBtn: { margin: 20, borderWidth: 1, borderColor: '#E5E7EB',
               borderRadius: 10, padding: 14, alignItems: 'center' },
  logoutText: { color: '#EF4444', fontWeight: '600', fontSize: 14 },
});
