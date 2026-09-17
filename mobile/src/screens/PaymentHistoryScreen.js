import React, { useState, useEffect } from 'react';
import {
  View, Text, FlatList, StyleSheet,
  ActivityIndicator, RefreshControl, TouchableOpacity
} from 'react-native';
import { Feather } from '@expo/vector-icons';
import { paymentsAPI } from '../services/api';

export default function PaymentHistoryScreen({ navigation }) {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    try {
      const res = await paymentsAPI.history();
      setTransactions(res.data.transactions);
    } catch (e) {
      console.log('History error:', e.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { load(); }, []);

  const renderItem = ({ item }) => (
    <View style={styles.txCard}>
      <View style={styles.txLeft}>
        <Feather
          name={item.status === 'confirmed' ? 'check-circle' :
                item.status === 'failed' ? 'x-circle' : 'clock'}
          size={22}
          color={item.status === 'confirmed' ? '#1A6E3C' :
                 item.status === 'failed' ? '#C0392B' : '#9CA3AF'}
        />
        <View>
          <Text style={styles.txLabel}>M-Pesa Top Up</Text>
          <Text style={styles.txRef}>
            {item.mpesa_reference || 'Pending...'}
          </Text>
          <Text style={styles.txDate}>
            {new Date(item.created_at).toLocaleDateString('en-KE', {
              day: 'numeric', month: 'short', year: 'numeric',
              hour: '2-digit', minute: '2-digit'
            })}
          </Text>
        </View>
      </View>
      <View style={styles.txRight}>
        <Text style={[styles.txAmount,
          item.status === 'confirmed' ? styles.txAmountGreen :
          item.status === 'failed' ? styles.txAmountRed : styles.txAmountGray]}>
          {item.status === 'confirmed' ? '+' : ''}KES {item.amount_ksh.toFixed(0)}
        </Text>
        <View style={[styles.statusBadge,
          item.status === 'confirmed' ? styles.badgeGreen :
          item.status === 'failed' ? styles.badgeRed : styles.badgeGray]}>
          <Text style={styles.statusText}>{item.status}</Text>
        </View>
      </View>
    </View>
  );

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#1A6E3C" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backRow}>
          <Feather name="arrow-left" size={14} color="#A8D8C0" />
          <Text style={styles.back}>Back</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Payment History</Text>
      </View>

      <FlatList
        data={transactions}
        keyExtractor={item => String(item.id)}
        renderItem={renderItem}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={refreshing}
            onRefresh={() => { setRefreshing(true); load(); }} />
        }
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyText}>No payments yet</Text>
            <Text style={styles.emptySub}>
              Your M-Pesa top-ups will appear here
            </Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F7F9FC' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { backgroundColor: '#1A3A5C', padding: 20, paddingTop: 52,
            flexDirection: 'row', alignItems: 'center', gap: 16 },
  backRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  back: { color: '#A8D8C0', fontSize: 14 },
  title: { color: '#fff', fontSize: 18, fontWeight: '700' },
  list: { padding: 16 },
  txCard: { backgroundColor: '#fff', borderRadius: 12, padding: 16,
            marginBottom: 10, flexDirection: 'row', justifyContent: 'space-between',
            alignItems: 'center', shadowColor: '#000',
            shadowOpacity: 0.04, shadowRadius: 6, elevation: 2 },
  txLeft: { flexDirection: 'row', alignItems: 'center', gap: 12, flex: 1 },
  txLabel: { fontSize: 14, fontWeight: '600', color: '#1A3A5C' },
  txRef: { fontSize: 11, color: '#9CA3AF', marginTop: 2 },
  txDate: { fontSize: 11, color: '#9CA3AF', marginTop: 1 },
  txRight: { alignItems: 'flex-end' },
  txAmount: { fontSize: 16, fontWeight: '700' },
  txAmountGreen: { color: '#1A6E3C' },
  txAmountRed: { color: '#C0392B' },
  txAmountGray: { color: '#6B7280' },
  statusBadge: { borderRadius: 10, paddingHorizontal: 8,
                 paddingVertical: 3, marginTop: 4 },
  badgeGreen: { backgroundColor: '#D1FAE5' },
  badgeRed: { backgroundColor: '#FEE2E2' },
  badgeGray: { backgroundColor: '#F3F4F6' },
  statusText: { fontSize: 10, fontWeight: '600', color: '#374151' },
  empty: { alignItems: 'center', paddingTop: 80 },
  emptyText: { fontSize: 18, fontWeight: '700', color: '#1A3A5C' },
  emptySub: { fontSize: 13, color: '#9CA3AF', marginTop: 8 },
});
