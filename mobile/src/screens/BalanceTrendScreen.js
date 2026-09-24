import React, { useState, useEffect } from 'react';
import {
  View, Text, StyleSheet, ActivityIndicator,
  TouchableOpacity, Dimensions, ScrollView
} from 'react-native';
import { LineChart } from 'react-native-chart-kit';
import { Feather } from '@expo/vector-icons';
import { paymentsAPI } from '../services/api';

const { width } = Dimensions.get('window');

export default function BalanceTrendScreen({ navigation, route }) {
  const mealAccountId = route.params?.meal_account_id;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedDays, setSelectedDays] = useState(30);

  useEffect(() => {
    loadTrend();
  }, [selectedDays]);

  const loadTrend = async () => {
    setLoading(true);
    try {
      const res = await paymentsAPI.balanceTrend(selectedDays, mealAccountId);
      setData(res.data);
    } catch (e) {
      console.log('Trend error:', e.message);
    } finally {
      setLoading(false);
    }
  };

  const chartData = data?.data_points || [];
  const balances = chartData.map(d => d.balance_ksh);
  const labels = chartData.length > 0
    ? chartData
        .filter((_, i) => i % Math.ceil(chartData.length / 6) === 0)
        .map(d => d.day)
    : [];

  const maxBalance = balances.length ? Math.max(...balances) : 0;
  const minBalance = balances.length ? Math.min(...balances) : 0;

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Feather name="arrow-left" size={22} color="#A8D8C0" />
        </TouchableOpacity>
        <Text style={styles.title}>Balance History</Text>
        <View style={{ width: 22 }} />
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.periodRow}>
          {[7, 14, 30].map(d => (
            <TouchableOpacity
              key={d}
              style={[styles.periodBtn, selectedDays === d && styles.periodBtnActive]}
              onPress={() => setSelectedDays(d)}
            >
              <Text style={[
                styles.periodBtnText, selectedDays === d && styles.periodBtnTextActive
              ]}>
                {d} days
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {loading ? (
          <ActivityIndicator color="#1A6E3C" size="large" style={{ marginTop: 60 }} />
        ) : data && balances.length > 0 ? (
          <>
            <View style={styles.currentBalance}>
              <Text style={styles.currentLabel}>Current Balance</Text>
              <Text style={styles.currentValue}>
                KES {data.current_balance_ksh?.toLocaleString(
                  'en-KE', { minimumFractionDigits: 2 })}
              </Text>
              <Text style={styles.studentName}>{data.student_name}</Text>
            </View>

            <LineChart
              data={{
                labels: labels.length > 0 ? labels : ['Start', 'End'],
                datasets: [{
                  data: balances.length > 0 ? balances : [0],
                  color: (opacity = 1) => `rgba(26, 110, 60, ${opacity})`,
                  strokeWidth: 2,
                }],
              }}
              width={width - 40}
              height={220}
              chartConfig={{
                backgroundColor: '#fff',
                backgroundGradientFrom: '#fff',
                backgroundGradientTo: '#fff',
                decimalPlaces: 0,
                color: (opacity = 1) => `rgba(26, 58, 92, ${opacity})`,
                labelColor: (opacity = 1) => `rgba(107, 114, 128, ${opacity})`,
                style: { borderRadius: 16 },
                propsForDots: { r: '3', strokeWidth: '1', stroke: '#1A6E3C' },
                propsForBackgroundLines: { strokeDasharray: '3', stroke: '#F3F4F6' },
              }}
              bezier
              style={styles.chart}
              withShadow={false}
              withInnerLines
              withOuterLines={false}
            />

            <View style={styles.legend}>
              <View style={styles.legendItem}>
                <View style={[styles.legendDot, { backgroundColor: '#1A6E3C' }]} />
                <Text style={styles.legendText}>Balance (KES)</Text>
              </View>
              <View style={styles.legendItem}>
                <Feather name="arrow-up" size={11} color="#1A6E3C" />
                <Text style={styles.legendText}>Top-up</Text>
                <Feather name="arrow-down" size={11} color="#C0392B" style={{ marginLeft: 8 }} />
                <Text style={styles.legendText}>Meal deduction</Text>
              </View>
            </View>

            <View style={styles.statsRow}>
              <View style={styles.statBox}>
                <Text style={styles.statVal}>
                  KES {maxBalance.toLocaleString('en-KE', { minimumFractionDigits: 0 })}
                </Text>
                <Text style={styles.statLabel}>Peak balance</Text>
              </View>
              <View style={styles.statBox}>
                <Text style={[
                  styles.statVal, { color: minBalance < 100 ? '#C0392B' : '#1A3A5C' }
                ]}>
                  KES {minBalance.toLocaleString('en-KE', { minimumFractionDigits: 0 })}
                </Text>
                <Text style={styles.statLabel}>Lowest balance</Text>
              </View>
            </View>

            <Text style={styles.eventsTitle}>Activity Log</Text>
            {chartData
              .filter(d => d.topped_up || d.meal_deducted)
              .reverse()
              .slice(0, 10)
              .map((d, i) => (
              <View key={i} style={styles.eventRow}>
                <View style={styles.eventIconWrap}>
                  <Feather
                    name={d.topped_up ? 'credit-card' : 'coffee'}
                    size={16}
                    color="#1A3A5C"
                  />
                </View>
                <View style={styles.eventContent}>
                  <Text style={styles.eventTitle}>
                    {d.topped_up ? 'Top-up received' : 'Meal collected'}
                  </Text>
                  <Text style={styles.eventDate}>{d.day}</Text>
                </View>
                <Text style={styles.eventBalance}>
                  KES {d.balance_ksh.toLocaleString('en-KE', { minimumFractionDigits: 2 })}
                </Text>
              </View>
            ))}
          </>
        ) : (
          <View style={styles.empty}>
            <Text style={styles.emptyText}>No balance history yet</Text>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F7F9FC' },
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    backgroundColor: '#1A3A5C', paddingTop: 52, paddingBottom: 16, paddingHorizontal: 20,
  },
  title: { color: '#fff', fontSize: 18, fontWeight: '700' },
  content: { padding: 20, paddingBottom: 40 },
  periodRow: { flexDirection: 'row', gap: 10, marginBottom: 20 },
  periodBtn: {
    flex: 1, borderWidth: 1, borderColor: '#E5E7EB', borderRadius: 8,
    paddingVertical: 8, alignItems: 'center', backgroundColor: '#fff',
  },
  periodBtnActive: { backgroundColor: '#1A3A5C', borderColor: '#1A3A5C' },
  periodBtnText: { fontSize: 13, fontWeight: '600', color: '#374151' },
  periodBtnTextActive: { color: '#fff' },
  currentBalance: {
    alignItems: 'center', marginBottom: 20, backgroundColor: '#fff', borderRadius: 12,
    padding: 16, shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 6, elevation: 2,
  },
  currentLabel: { fontSize: 12, color: '#6B7280' },
  currentValue: { fontSize: 28, fontWeight: '700', color: '#1A3A5C', marginTop: 4 },
  studentName: { fontSize: 12, color: '#9CA3AF', marginTop: 4 },
  chart: { borderRadius: 12, marginBottom: 12 },
  legend: { flexDirection: 'row', gap: 16, marginBottom: 16, justifyContent: 'center' },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  legendDot: { width: 10, height: 10, borderRadius: 5 },
  legendText: { fontSize: 11, color: '#6B7280' },
  statsRow: { flexDirection: 'row', gap: 12, marginBottom: 20 },
  statBox: {
    flex: 1, backgroundColor: '#fff', borderRadius: 12, padding: 14, alignItems: 'center',
    shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 6, elevation: 2,
  },
  statVal: { fontSize: 16, fontWeight: '700', color: '#1A3A5C' },
  statLabel: { fontSize: 11, color: '#6B7280', marginTop: 4 },
  eventsTitle: { fontSize: 14, fontWeight: '700', color: '#1A3A5C', marginBottom: 10 },
  eventRow: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff',
    borderRadius: 10, padding: 12, marginBottom: 8, gap: 10,
  },
  eventIconWrap: {
    width: 32, height: 32, borderRadius: 16, backgroundColor: '#F7F9FC',
    alignItems: 'center', justifyContent: 'center',
  },
  eventContent: { flex: 1 },
  eventTitle: { fontSize: 13, fontWeight: '600', color: '#1A3A5C' },
  eventDate: { fontSize: 11, color: '#9CA3AF', marginTop: 2 },
  eventBalance: { fontSize: 13, fontWeight: '700', color: '#1A3A5C' },
  empty: { alignItems: 'center', paddingTop: 60 },
  emptyText: { fontSize: 16, color: '#9CA3AF' },
});
