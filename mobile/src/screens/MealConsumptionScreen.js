import React, { useState, useEffect } from 'react';
import {
  View, Text, FlatList, StyleSheet,
  ActivityIndicator, RefreshControl, TouchableOpacity
} from 'react-native';
import { Feather, MaterialCommunityIcons } from '@expo/vector-icons';
import { mealsAPI } from '../services/api';

export default function MealConsumptionScreen({ navigation }) {
  const [studentName, setStudentName] = useState('');
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    try {
      const res = await mealsAPI.consumption();
      setStudentName(res.data.student_name);
      setEvents(res.data.events);
    } catch (e) {
      console.log('Consumption error:', e.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { load(); }, []);

  const renderItem = ({ item }) => (
    <View style={styles.card}>
      <View style={styles.cardTop}>
        <MaterialCommunityIcons name="silverware-fork-knife" size={18} color="#1A6E3C" />
        <Text style={styles.mealDate}>
          {new Date(item.meal_date).toLocaleDateString('en-KE', {
            weekday: 'short', day: 'numeric', month: 'short'
          })}
        </Text>
        <Text style={styles.mealAmount}>KES {item.amount_ksh.toFixed(2)}</Text>
      </View>
      <Text style={styles.items}>
        {item.items && item.items.length > 0
          ? item.items.map(i => i.name).join(', ')
          : 'No items recorded'}
      </Text>
      <Text style={styles.servedBy}>
        Served by {item.served_by_name || 'kitchen staff'}
        {item.served_by_email ? ` (${item.served_by_email})` : ''}
      </Text>
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
        <Text style={styles.title}>Meal Consumption</Text>
        {studentName ? <Text style={styles.subtitle}>{studentName}</Text> : null}
      </View>

      <FlatList
        data={events}
        keyExtractor={item => String(item.id)}
        renderItem={renderItem}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={refreshing}
            onRefresh={() => { setRefreshing(true); load(); }} />
        }
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyText}>No meals recorded yet</Text>
            <Text style={styles.emptySub}>
              Meals served at school will appear here
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
  header: { backgroundColor: '#1A3A5C', padding: 20, paddingTop: 52 },
  backRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 8 },
  back: { color: '#A8D8C0', fontSize: 14 },
  title: { color: '#fff', fontSize: 18, fontWeight: '700' },
  subtitle: { color: '#6B9AB8', fontSize: 12, marginTop: 4 },
  list: { padding: 16 },
  card: { backgroundColor: '#fff', borderRadius: 12, padding: 16,
          marginBottom: 10, shadowColor: '#000',
          shadowOpacity: 0.04, shadowRadius: 6, elevation: 2 },
  cardTop: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  mealDate: { fontSize: 13, fontWeight: '600', color: '#1A3A5C', flex: 1 },
  mealAmount: { fontSize: 14, fontWeight: '700', color: '#1A3A5C' },
  items: { fontSize: 13, color: '#374151', marginTop: 8 },
  servedBy: { fontSize: 11, color: '#9CA3AF', marginTop: 6 },
  empty: { alignItems: 'center', paddingTop: 80 },
  emptyText: { fontSize: 18, fontWeight: '700', color: '#1A3A5C' },
  emptySub: { fontSize: 13, color: '#9CA3AF', marginTop: 8 },
});
