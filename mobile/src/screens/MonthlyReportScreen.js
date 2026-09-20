import React, { useState, useEffect } from 'react';
import {
  View, Text, StyleSheet, ActivityIndicator,
  TouchableOpacity, ScrollView, Dimensions
} from 'react-native';
import { BarChart } from 'react-native-chart-kit';
import { Feather } from '@expo/vector-icons';
import { paymentsAPI } from '../services/api';

const { width } = Dimensions.get('window');

export default function MonthlyReportScreen({ navigation, route }) {
  const mealAccountId = route.params?.meal_account_id;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [months, setMonths] = useState(3);

  useEffect(() => {
    loadReport();
  }, [months]);

  const loadReport = async () => {
    setLoading(true);
    try {
      const res = await paymentsAPI.monthlyReport(months, mealAccountId);
      setData(res.data);
    } catch (e) {
      console.log('Monthly report error:', e.message);
    } finally {
      setLoading(false);
    }
  };

  const chartData = data?.monthly_data || [];
  const mealsChartData = {
    labels: chartData.map(m => m.month_short),
    datasets: [{ data: chartData.map(m => m.meals_collected || 0) }]
  };
  const change = data?.meals_change_vs_last_month ?? 0;

  const summaryCards = data ? [
    { label: 'Meals this month', val: data.total_meals_this_month,
      icon: 'coffee', color: '#1A6E3C' },
    { label: 'Spent this month', val: `KES ${data.total_spent_this_month_ksh}`,
      icon: 'arrow-down-circle', color: '#C0392B' },
    { label: 'Topped up this month',
      val: `KES ${data.total_topped_up_this_month_ksh?.toLocaleString()}`,
      icon: 'arrow-up-circle', color: '#3A4AB0' },
    { label: 'vs last month',
      val: change >= 0 ? `+${change} meals` : `${change} meals`,
      icon: change >= 0 ? 'trending-up' : 'trending-down',
      color: change >= 0 ? '#1A6E3C' : '#C0392B' },
  ] : [];

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Feather name="arrow-left" size={22} color="#A8D8C0" />
        </TouchableOpacity>
        <Text style={styles.title}>Monthly Report</Text>
        <View style={{ width: 22 }} />
      </View>

      <View style={styles.content}>
        <View style={styles.periodRow}>
          {[1, 3, 6].map(m => (
            <TouchableOpacity
              key={m}
              style={[styles.periodBtn, months === m && styles.periodBtnActive]}
              onPress={() => setMonths(m)}
            >
              <Text style={[
                styles.periodBtnText, months === m && styles.periodBtnTextActive
              ]}>
                {m} {m === 1 ? 'month' : 'months'}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {loading ? (
          <ActivityIndicator color="#1A6E3C" size="large" style={{ marginTop: 60 }} />
        ) : data ? (
          <>
            <Text style={styles.studentLabel}>Report for {data.student_name}</Text>

            <View style={styles.summaryGrid}>
              {summaryCards.map(s => (
                <View key={s.label} style={styles.summaryCard}>
                  <Feather name={s.icon} size={22} color={s.color} style={{ marginBottom: 6 }} />
                  <Text style={[styles.summaryVal, { color: s.color }]}>{s.val}</Text>
                  <Text style={styles.summaryLabel}>{s.label}</Text>
                </View>
              ))}
            </View>

            {chartData.length > 1 && (
              <View style={styles.chartCard}>
                <Text style={styles.chartTitle}>Meals Collected per Month</Text>
                <BarChart
                  data={mealsChartData}
                  width={width - 80}
                  height={160}
                  chartConfig={{
                    backgroundColor: '#fff',
                    backgroundGradientFrom: '#fff',
                    backgroundGradientTo: '#fff',
                    decimalPlaces: 0,
                    color: (o = 1) => `rgba(26, 110, 60, ${o})`,
                    labelColor: (o = 1) => `rgba(107, 114, 128, ${o})`,
                  }}
                  style={{ borderRadius: 8 }}
                  withInnerLines={false}
                  showValuesOnTopOfBars
                  fromZero
                />
              </View>
            )}

            <Text style={styles.sectionTitle}>Monthly Breakdown</Text>
            {chartData.slice().reverse().map((m, i) => (
              <View key={i} style={styles.monthCard}>
                <View style={styles.monthHeader}>
                  <Text style={styles.monthName}>{m.month}</Text>
                  <Text style={styles.monthMeals}>{m.meals_collected} meals</Text>
                </View>
                <View style={styles.monthStats}>
                  <View style={styles.monthStat}>
                    <Text style={styles.monthStatLabel}>Spent</Text>
                    <Text style={[styles.monthStatVal, { color: '#C0392B' }]}>
                      KES {m.meals_cost_ksh?.toLocaleString()}
                    </Text>
                  </View>
                  <View style={styles.monthStat}>
                    <Text style={styles.monthStatLabel}>Topped Up</Text>
                    <Text style={[styles.monthStatVal, { color: '#1A6E3C' }]}>
                      KES {m.total_topped_up_ksh?.toLocaleString(
                        'en-KE', { minimumFractionDigits: 2 })}
                    </Text>
                  </View>
                  <View style={styles.monthStat}>
                    <Text style={styles.monthStatLabel}>Daily avg</Text>
                    <Text style={styles.monthStatVal}>KES {m.avg_cost_per_day}</Text>
                  </View>
                  <View style={styles.monthStat}>
                    <Text style={styles.monthStatLabel}>Top-ups</Text>
                    <Text style={styles.monthStatVal}>{m.num_top_ups}x</Text>
                  </View>
                </View>
              </View>
            ))}
          </>
        ) : (
          <View style={styles.empty}>
            <Text style={styles.emptyText}>No report data available</Text>
          </View>
        )}
      </View>
    </ScrollView>
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
  studentLabel: { fontSize: 13, color: '#6B7280', marginBottom: 16, textAlign: 'center' },
  summaryGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 20 },
  summaryCard: {
    width: '47%', backgroundColor: '#fff', borderRadius: 12, padding: 14,
    alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.04,
    shadowRadius: 6, elevation: 2,
  },
  summaryVal: { fontSize: 16, fontWeight: '700', marginBottom: 4 },
  summaryLabel: { fontSize: 10, color: '#6B7280', textAlign: 'center' },
  chartCard: {
    backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 20,
    shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 6, elevation: 2,
    alignItems: 'center',
  },
  chartTitle: {
    fontSize: 14, fontWeight: '700', color: '#1A3A5C',
    marginBottom: 12, alignSelf: 'flex-start',
  },
  sectionTitle: { fontSize: 14, fontWeight: '700', color: '#1A3A5C', marginBottom: 10 },
  monthCard: {
    backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 10,
    shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 6, elevation: 2,
  },
  monthHeader: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    marginBottom: 12, paddingBottom: 10, borderBottomWidth: 1, borderBottomColor: '#F3F4F6',
  },
  monthName: { fontSize: 15, fontWeight: '700', color: '#1A3A5C' },
  monthMeals: { fontSize: 13, fontWeight: '600', color: '#1A6E3C' },
  monthStats: { flexDirection: 'row', justifyContent: 'space-between' },
  monthStat: { alignItems: 'center' },
  monthStatLabel: { fontSize: 10, color: '#9CA3AF' },
  monthStatVal: { fontSize: 13, fontWeight: '700', color: '#1A3A5C', marginTop: 2 },
  empty: { alignItems: 'center', paddingTop: 60 },
  emptyText: { fontSize: 16, color: '#9CA3AF' },
});
