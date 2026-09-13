import React, { useState, useCallback } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, FlatList,
  StyleSheet, ActivityIndicator, Alert
} from 'react-native';
import { useAuth } from '../context/AuthContext';
import { mealsAPI } from '../services/api';

export default function KitchenServeScreen() {
  const { user, logout } = useAuth();
  const [query, setQuery] = useState('');
  const [students, setStudents] = useState([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [servingId, setServingId] = useState(null);

  const runSearch = useCallback(async (q) => {
    if (!q || q.trim().length < 2) {
      setStudents([]);
      setSearched(false);
      return;
    }
    setLoading(true);
    try {
      const res = await mealsAPI.lookup(q.trim());
      setStudents(res.data.students);
      setSearched(true);
    } catch (e) {
      Alert.alert('Search failed', e.response?.data?.error || 'Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleServe = (student) => {
    Alert.alert(
      'Confirm meal',
      `Serve a meal to ${student.full_name}?\nKES 50.00 will be deducted (balance: KES ${student.balance_ksh.toFixed(2)}).`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Serve',
          onPress: async () => {
            setServingId(student.id);
            try {
              const res = await mealsAPI.serve(student.id);
              Alert.alert(
                'Meal recorded',
                `${res.data.student} — new balance KES ${res.data.new_balance_ksh.toFixed(2)}`
              );
              runSearch(query);
            } catch (e) {
              Alert.alert('Could not record meal', e.response?.data?.error || 'Please try again.');
            } finally {
              setServingId(null);
            }
          }
        }
      ]
    );
  };

  const handleLogout = () => {
    Alert.alert('Log out', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Log out', style: 'destructive', onPress: logout }
    ]);
  };

  const renderItem = ({ item }) => {
    const disabled = !item.eligible || servingId === item.id;
    return (
      <View style={styles.card}>
        <View style={styles.cardInfo}>
          <Text style={styles.studentName}>{item.full_name}</Text>
          <Text style={styles.studentBalance}>
            KES {item.balance_ksh.toFixed(2)}
          </Text>
          {item.already_served_today && (
            <Text style={styles.badgeServed}>✅ Already served today</Text>
          )}
          {!item.already_served_today && item.is_low_balance && (
            <Text style={styles.badgeLow}>⚠️ Low balance</Text>
          )}
        </View>
        <TouchableOpacity
          style={[styles.serveBtn, disabled && styles.serveBtnDisabled]}
          onPress={() => handleServe(item)}
          disabled={disabled}
        >
          {servingId === item.id
            ? <ActivityIndicator color="#fff" size="small" />
            : <Text style={styles.serveBtnText}>
                {item.already_served_today ? 'Served' : 'Serve'}
              </Text>
          }
        </TouchableOpacity>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>Kitchen · {user?.school?.name}</Text>
          <Text style={styles.name}>{user?.full_name}</Text>
        </View>
        <TouchableOpacity onPress={handleLogout}>
          <Text style={styles.logout}>Log out</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.searchWrap}>
        <TextInput
          style={styles.searchInput}
          placeholder="Search student by name..."
          placeholderTextColor="#9CA3AF"
          value={query}
          onChangeText={(v) => { setQuery(v); runSearch(v); }}
          autoCapitalize="words"
        />
      </View>

      {loading ? (
        <ActivityIndicator size="large" color="#1A6E3C" style={{ marginTop: 40 }} />
      ) : (
        <FlatList
          data={students}
          keyExtractor={(item) => String(item.id)}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Text style={styles.emptyText}>
                {searched ? 'No students found' : 'Type a name to search'}
              </Text>
              <Text style={styles.emptySub}>
                {searched
                  ? 'Try a different spelling'
                  : 'e.g. "John" or "Wanjiku"'}
              </Text>
            </View>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F7F9FC' },
  header: { backgroundColor: '#1A3A5C', padding: 20, paddingTop: 56,
            flexDirection: 'row', justifyContent: 'space-between',
            alignItems: 'flex-start' },
  greeting: { color: '#A8D8C0', fontSize: 12 },
  name: { color: '#fff', fontSize: 18, fontWeight: '700', marginTop: 2 },
  logout: { color: '#F87171', fontSize: 13, marginTop: 4 },
  searchWrap: { padding: 16 },
  searchInput: { backgroundColor: '#fff', borderWidth: 1, borderColor: '#E5E7EB',
                 borderRadius: 10, paddingHorizontal: 16, paddingVertical: 12,
                 fontSize: 15, color: '#111827' },
  list: { paddingHorizontal: 16, paddingBottom: 24 },
  card: { backgroundColor: '#fff', borderRadius: 12, padding: 16,
          marginBottom: 10, flexDirection: 'row', justifyContent: 'space-between',
          alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.04,
          shadowRadius: 6, elevation: 2 },
  cardInfo: { flex: 1 },
  studentName: { fontSize: 15, fontWeight: '700', color: '#1A3A5C' },
  studentBalance: { fontSize: 13, color: '#6B7280', marginTop: 2 },
  badgeServed: { fontSize: 12, color: '#1A6E3C', marginTop: 4, fontWeight: '600' },
  badgeLow: { fontSize: 12, color: '#D07020', marginTop: 4, fontWeight: '600' },
  serveBtn: { backgroundColor: '#1A6E3C', borderRadius: 8,
              paddingVertical: 10, paddingHorizontal: 18 },
  serveBtnDisabled: { backgroundColor: '#CBD5E1' },
  serveBtnText: { color: '#fff', fontSize: 13, fontWeight: '700' },
  empty: { alignItems: 'center', paddingTop: 60 },
  emptyText: { fontSize: 16, fontWeight: '700', color: '#1A3A5C' },
  emptySub: { fontSize: 13, color: '#9CA3AF', marginTop: 6 },
});
