import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { mealsAPI } from '../services/api';

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];

function mondayOf(d) {
  const dayOfWeek = d.getDay();
  const monday = new Date(d);
  monday.setDate(d.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1));
  monday.setHours(0, 0, 0, 0);
  return monday;
}

export default function WeeklyMealSummary({ mealAccountId }) {
  const [weekData, setWeekData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [totalMeals, setTotalMeals] = useState(0);
  const [totalCost, setTotalCost] = useState(0);

  useEffect(() => {
    loadWeekData();
  }, [mealAccountId]);

  const loadWeekData = async () => {
    setLoading(true);
    try {
      const today = new Date();
      const monday = mondayOf(today);
      const todayStr = today.toISOString().split('T')[0];

      // One call for the whole account, then group locally — the
      // admin-scoped daily log endpoint would need one request per day
      // and isn't even reachable by a parent/student account.
      const res = await mealsAPI.consumption(mealAccountId);
      const events = res.data.events || [];
      const eventsByDate = new Set(events.map(e => e.meal_date));

      let mealsCount = 0;
      let costCents = 0;
      const weekDays = DAYS.map((day, i) => {
        const d = new Date(monday);
        d.setDate(monday.getDate() + i);
        const dateStr = d.toISOString().split('T')[0];
        const isPast = dateStr <= todayStr;
        const ate = isPast && eventsByDate.has(dateStr);
        if (ate) {
          mealsCount++;
          const ev = events.find(e => e.meal_date === dateStr);
          costCents += (ev?.amount_ksh || 0) * 100;
        }
        return { day, date: dateStr, ate, isPast, isToday: dateStr === todayStr };
      });

      setWeekData(weekDays);
      setTotalMeals(mealsCount);
      setTotalCost(costCents / 100);
    } catch (e) {
      console.log('Week data error:', e.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.card}>
        <ActivityIndicator color="#1A6E3C" />
      </View>
    );
  }

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Text style={styles.title}>This Week</Text>
        <Text style={styles.summary}>
          {totalMeals}/5 meals · KES {totalCost.toLocaleString('en-KE')}
        </Text>
      </View>

      <View style={styles.daysRow}>
        {weekData.map((day, i) => (
          <View key={i} style={styles.dayCol}>
            <Text style={styles.dayLabel}>{day.day}</Text>
            <View style={[
              styles.dayCircle,
              day.ate && styles.dayCircleAte,
              day.isToday && styles.dayCircleToday,
              !day.isPast && styles.dayCircleFuture,
            ]}>
              {day.isPast ? (
                <Feather
                  name={day.ate ? 'check' : 'x'}
                  size={16}
                  color={day.ate ? '#1A6E3C' : '#C0392B'}
                />
              ) : (
                <Text style={styles.dayCircleTextFuture}>—</Text>
              )}
            </View>
          </View>
        ))}
      </View>

      <View style={styles.footer}>
        {totalMeals === 5 ? (
          <View style={styles.footerRow}>
            <Feather name="award" size={13} color="#6B7280" />
            <Text style={styles.footerText}>Perfect attendance this week!</Text>
          </View>
        ) : (
          <Text style={styles.footerText}>
            {totalMeals === 0
              ? 'No meals collected yet this week'
              : `${5 - totalMeals} day${5 - totalMeals > 1 ? 's' : ''} remaining this week`}
          </Text>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff', borderRadius: 16,
    padding: 16, marginHorizontal: 20, marginTop: 12,
    shadowColor: '#000', shadowOpacity: 0.05,
    shadowRadius: 8, elevation: 2,
  },
  header: {
    flexDirection: 'row', justifyContent: 'space-between',
    alignItems: 'center', marginBottom: 14,
  },
  title: { fontSize: 14, fontWeight: '700', color: '#1A3A5C' },
  summary: { fontSize: 12, color: '#1A6E3C', fontWeight: '600' },
  daysRow: {
    flexDirection: 'row', justifyContent: 'space-around', marginBottom: 12,
  },
  dayCol: { alignItems: 'center', gap: 6 },
  dayLabel: { fontSize: 11, color: '#6B7280', fontWeight: '600' },
  dayCircle: {
    width: 36, height: 36, borderRadius: 18,
    backgroundColor: '#FEE2E2', alignItems: 'center', justifyContent: 'center',
    borderWidth: 1, borderColor: '#FECACA',
  },
  dayCircleAte: { backgroundColor: '#D1FAE5', borderColor: '#A7F3D0' },
  dayCircleToday: { borderWidth: 2, borderColor: '#1A6E3C' },
  dayCircleFuture: { backgroundColor: '#F3F4F6', borderColor: '#E5E7EB' },
  dayCircleTextFuture: { fontSize: 14, color: '#9CA3AF' },
  footer: {
    backgroundColor: '#F7F9FC', borderRadius: 8,
    padding: 8, alignItems: 'center',
  },
  footerRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  footerText: { fontSize: 12, color: '#6B7280' },
});
