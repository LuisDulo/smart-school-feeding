import React, { useState, useCallback, useEffect } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet,
  Alert, ScrollView, RefreshControl
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { Feather, MaterialCommunityIcons } from '@expo/vector-icons';
import { useAuth } from '../context/AuthContext';
import { paymentsAPI } from '../services/api';
import ChildSelector from '../components/ChildSelector';
import WeeklyMealSummary from '../components/WeeklyMealSummary';
import RiskAlertBanner from '../components/RiskAlertBanner';
import NotificationBell from '../components/NotificationBell';

const LOW_BALANCE_THRESHOLD_CENTS = 10000; // KES 100
// A parent has no meal_account of their own — the backend resolves
// /api/payments/balance/ and /history/ to their child's account instead
// (see resolve_meal_account in payments/views.py), so parents can see the
// same balance/history/low-balance UI as a student.
const CAN_VIEW_BALANCE = ['student', 'parent'];

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

export default function HomeScreen({ navigation }) {
  const { user, logout } = useAuth();
  const [balanceCents, setBalanceCents] = useState(
    user?.role === 'student' ? (user?.balance_cents ?? null) : null
  );
  // Whose balance this is — the logged-in student, or a parent's selected
  // child. Falls back to the logged-in user's own name until the first
  // fetch resolves (only matters for the brief instant before that
  // response).
  const [studentName, setStudentName] = useState(user?.full_name ?? '');
  const [selectedChild, setSelectedChild] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  // The meal_account id to scope every balance-aware request to — the
  // parent's selected child, once ChildSelector has loaded (undefined
  // until then, which resolve_meal_account treats as "first linked
  // child", so single-child parents and students are unaffected).
  const mealAccountId = selectedChild?.id;

  const loadBalance = useCallback(async () => {
    if (!CAN_VIEW_BALANCE.includes(user?.role)) return;
    try {
      const res = await paymentsAPI.balance(mealAccountId);
      setBalanceCents(res.data.balance_cents);
      setStudentName(res.data.student_name);
    } catch (e) {
      console.log('Balance error:', e.message);
    }
  }, [user?.role, mealAccountId]);

  // Re-fetch the live balance every time Home comes into focus (e.g. after
  // returning from a confirmed top-up) or the selected child changes.
  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      (async () => {
        if (cancelled) return;
        await loadBalance();
      })();
      return () => { cancelled = true; };
    }, [loadBalance])
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

  const onRefresh = async () => {
    setRefreshing(true);
    await loadBalance();
    setRefreshing(false);
  };

  const handleLogout = () => {
    Alert.alert('Log out', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Log out', style: 'destructive', onPress: logout }
    ]);
  };

  const balanceKsh = balanceCents != null ? (balanceCents / 100).toFixed(2) : '0.00';
  const isLow = balanceCents != null && balanceCents < LOW_BALANCE_THRESHOLD_CENTS;

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#1A6E3C" />
      }
    >
      <View style={styles.header}>
        <View style={styles.headerTop}>
          <View style={{ flex: 1 }}>
            <View style={styles.greetingRow}>
              <Text style={styles.greeting}>{getGreeting()}</Text>
              <MaterialCommunityIcons name="hand-wave-outline" size={15} color="#A8D8C0" />
            </View>
            <Text style={styles.name}>{user?.full_name}</Text>
            <Text style={styles.role}>{user?.school?.name} · {user?.role}</Text>
          </View>
          {CAN_VIEW_BALANCE.includes(user?.role) && <NotificationBell mealAccountId={mealAccountId} />}
        </View>

        {/* Child selector — only renders if the parent has multiple children */}
        {user?.role === 'parent' && (
          <ChildSelector selectedChild={selectedChild} onSelectChild={setSelectedChild} />
        )}
      </View>

      {CAN_VIEW_BALANCE.includes(user?.role) && (
        <RiskAlertBanner navigation={navigation} mealAccountId={mealAccountId} />
      )}

      {CAN_VIEW_BALANCE.includes(user?.role) && (
        <View style={[styles.balanceCard, isLow && styles.balanceCardLow]}>
          <Text style={styles.balanceLabel}>
            {user?.role === 'parent' ? `${studentName}'s Meal Balance` : 'Meal Account Balance'}
          </Text>
          <Text style={[styles.balanceAmount, isLow && styles.balanceAmountLow]}>
            KES {balanceKsh}
          </Text>
          {isLow && (
            <View style={styles.lowBadge}>
              <Feather name="alert-triangle" size={12} color="#D07020" />
              <Text style={styles.lowBadgeText}>Low balance — tap Top Up to add funds</Text>
            </View>
          )}
          <TouchableOpacity
            style={styles.topUpQuick}
            onPress={() => navigation.navigate('TopUp')}
          >
            <Text style={styles.topUpQuickText}>+ Top Up</Text>
          </TouchableOpacity>
        </View>
      )}

      {CAN_VIEW_BALANCE.includes(user?.role) && (
        <WeeklyMealSummary mealAccountId={mealAccountId} />
      )}

      <View style={styles.actions}>
        <TouchableOpacity style={styles.actionBtn} onPress={() => navigation.navigate('TopUp')}>
          <Feather name="credit-card" size={26} color="#1A6E3C" style={styles.actionIcon} />
          <Text style={styles.actionLabel}>Top Up</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.actionBtn} onPress={() => navigation.navigate('PaymentHistory')}>
          <Feather name="clipboard" size={26} color="#1A6E3C" style={styles.actionIcon} />
          <Text style={styles.actionLabel}>History</Text>
        </TouchableOpacity>
      </View>

      {CAN_VIEW_BALANCE.includes(user?.role) && (
        <View style={styles.actions}>
          <TouchableOpacity
            style={styles.actionBtn}
            onPress={() => navigation.navigate('MealConsumption')}
          >
            <MaterialCommunityIcons name="silverware-fork-knife" size={26} color="#1A6E3C" style={styles.actionIcon} />
            <Text style={styles.actionLabel}>Meals Eaten</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.actionBtn}
            onPress={() => navigation.navigate('BalanceTrend', { meal_account_id: mealAccountId })}
          >
            <Feather name="trending-up" size={26} color="#1A3A5C" style={styles.actionIcon} />
            <Text style={styles.actionLabel}>Balance Trend</Text>
          </TouchableOpacity>
        </View>
      )}

      {CAN_VIEW_BALANCE.includes(user?.role) && (
        <View style={styles.actions}>
          <TouchableOpacity
            style={styles.actionBtn}
            onPress={() => navigation.navigate('MonthlyReport', { meal_account_id: mealAccountId })}
          >
            <Feather name="calendar" size={26} color="#C0392B" style={styles.actionIcon} />
            <Text style={styles.actionLabel}>Monthly Report</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.actionBtn}
            onPress={() => navigation.navigate('QRCode', { meal_account_id: mealAccountId })}
          >
            <MaterialCommunityIcons name="qrcode" size={26} color="#1A6E3C" style={styles.actionIcon} />
            <Text style={styles.actionLabel}>My QR Code</Text>
          </TouchableOpacity>
        </View>
      )}

      {user?.role === 'parent' && (
        <View style={styles.actions}>
          <TouchableOpacity
            style={styles.actionBtn}
            onPress={() => navigation.navigate('ApplyCredit')}
          >
            <Feather name="trending-up" size={26} color="#9673a6" style={styles.actionIcon} />
            <Text style={styles.actionLabel}>Apply for Credit</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.actionBtn}
            onPress={() => navigation.navigate('ReminderSettings')}
          >
            <Feather name="bell" size={26} color="#D07020" style={styles.actionIcon} />
            <Text style={styles.actionLabel}>Reminders</Text>
          </TouchableOpacity>
        </View>
      )}

      {user?.role === 'parent' && (
        <View style={styles.actions}>
          <TouchableOpacity
            style={[styles.actionBtn, styles.actionBtnWide]}
            onPress={() => navigation.navigate('RaiseIssue')}
          >
            <Feather name="alert-circle" size={26} color="#1A6E3C" style={styles.actionIcon} />
            <Text style={styles.actionLabel}>Raise an Issue</Text>
          </TouchableOpacity>
        </View>
      )}

      <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
        <Text style={styles.logoutText}>Log out</Text>
      </TouchableOpacity>

      <View style={{ height: 20 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F7F9FC' },
  header: { backgroundColor: '#1A3A5C', padding: 28, paddingTop: 60 },
  headerTop: { flexDirection: 'row', alignItems: 'flex-start' },
  greetingRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  greeting: { color: '#A8D8C0', fontSize: 14 },
  name: { color: '#fff', fontSize: 22, fontWeight: '700', marginTop: 4 },
  role: { color: '#6B9AB8', fontSize: 12, marginTop: 4 },
  balanceCard: { margin: 20, backgroundColor: '#fff', borderRadius: 16,
                 padding: 24, shadowColor: '#000', shadowOpacity: 0.06,
                 shadowRadius: 12, elevation: 3, alignItems: 'center' },
  balanceCardLow: { borderWidth: 2, borderColor: '#FCD34D' },
  balanceLabel: { fontSize: 13, color: '#6B7280' },
  balanceAmount: { fontSize: 36, fontWeight: '700', color: '#1A3A5C' },
  balanceAmountLow: { color: '#C0392B' },
  lowBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    backgroundColor: '#FEF3C7', borderRadius: 8, padding: 8, marginTop: 10,
  },
  lowBadgeText: { fontSize: 12, color: '#D07020', fontWeight: '600' },
  topUpQuick: {
    marginTop: 14, backgroundColor: '#1A6E3C', borderRadius: 20,
    paddingVertical: 8, paddingHorizontal: 24,
  },
  topUpQuickText: { color: '#fff', fontSize: 14, fontWeight: '700' },
  actions: { flexDirection: 'row', gap: 12, margin: 20, marginTop: 8 },
  actionBtn: { flex: 1, backgroundColor: '#fff', borderRadius: 12,
               padding: 20, alignItems: 'center',
               shadowColor: '#000', shadowOpacity: 0.04,
               shadowRadius: 6, elevation: 2 },
  actionBtnWide: { flex: 1 },
  actionIcon: { marginBottom: 8 },
  actionLabel: { fontSize: 13, fontWeight: '600', color: '#374151', textAlign: 'center' },
  logoutBtn: { margin: 20, borderWidth: 1, borderColor: '#E5E7EB',
               borderRadius: 10, padding: 14, alignItems: 'center' },
  logoutText: { color: '#EF4444', fontWeight: '600', fontSize: 14 },
});
