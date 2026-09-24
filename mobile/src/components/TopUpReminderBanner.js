import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Feather } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';

function todayKey() {
  return new Date().toISOString().split('T')[0];
}

export default function TopUpReminderBanner({ navigation }) {
  const [due, setDue] = useState(null); // { day, hour, studentName } | null

  useEffect(() => {
    checkReminder();
  }, []);

  const checkReminder = async () => {
    try {
      const raw = await AsyncStorage.getItem('reminder_settings');
      if (!raw) return;
      const settings = JSON.parse(raw);
      if (!settings.enabled) return;

      const now = new Date();
      if (now.getDay() !== settings.day || now.getHours() < settings.hour) return;

      const lastShown = await AsyncStorage.getItem('reminder_last_shown');
      if (lastShown === todayKey()) return;

      const userData = await AsyncStorage.getItem('user_data');
      const studentName = userData ? JSON.parse(userData).full_name : '';
      setDue({ studentName });
    } catch (e) {
      console.log('Reminder check error:', e.message);
    }
  };

  const markShown = () => AsyncStorage.setItem('reminder_last_shown', todayKey());

  const handleTopUp = async () => {
    await markShown();
    navigation.navigate('TopUp');
  };

  const handleDismiss = async () => {
    await markShown();
    setDue(null);
  };

  if (!due) return null;

  return (
    <View style={styles.banner}>
      <View style={styles.content}>
        <Feather name="bell" size={22} color="#3A4AB0" style={styles.icon} />
        <View style={styles.textWrap}>
          <Text style={styles.title}>Top Up Reminder</Text>
          <Text style={styles.sub}>
            Don't forget to top up {due.studentName}'s meal account this week.
          </Text>
        </View>
      </View>
      <View style={styles.actions}>
        <TouchableOpacity style={styles.topUpBtn} onPress={handleTopUp}>
          <Text style={styles.topUpBtnText}>Top Up Now</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.dismissBtn} onPress={handleDismiss}>
          <Text style={styles.dismissText}>Dismiss</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    marginHorizontal: 20, marginTop: 12, borderRadius: 16, padding: 16,
    backgroundColor: '#EEF0FB',
    shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 8, elevation: 3,
  },
  content: { flexDirection: 'row', gap: 12, marginBottom: 12 },
  icon: { marginTop: 2 },
  textWrap: { flex: 1 },
  title: { fontSize: 14, fontWeight: '700', color: '#1A3A5C', marginBottom: 4 },
  sub: { fontSize: 12, color: '#374151', lineHeight: 18 },
  actions: { flexDirection: 'row', gap: 10 },
  topUpBtn: {
    flex: 1, backgroundColor: '#1A6E3C', borderRadius: 8,
    paddingVertical: 10, alignItems: 'center',
  },
  topUpBtnText: { color: '#fff', fontSize: 13, fontWeight: '700' },
  dismissBtn: {
    paddingVertical: 10, paddingHorizontal: 16,
    borderWidth: 1, borderColor: '#D1D5DB', borderRadius: 8,
    alignItems: 'center', backgroundColor: '#fff',
  },
  dismissText: { color: '#6B7280', fontSize: 13, fontWeight: '600' },
});
