import React, { useState, useEffect } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity,
  Switch, Alert, ScrollView
} from 'react-native';
import { Feather } from '@expo/vector-icons';
import * as Notifications from 'expo-notifications';
import AsyncStorage from '@react-native-async-storage/async-storage';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

// weekday: 1-7, 1 = Sunday (expo-notifications' WeeklyTriggerInput convention).
const REMINDER_DAYS = [
  { label: 'Monday', value: 2 },
  { label: 'Tuesday', value: 3 },
  { label: 'Wednesday', value: 4 },
  { label: 'Thursday', value: 5 },
  { label: 'Friday', value: 6 },
];

const REMINDER_TIMES = [
  { label: '7:00 AM', hour: 7 },
  { label: '8:00 AM', hour: 8 },
  { label: '9:00 AM', hour: 9 },
  { label: '12:00 PM', hour: 12 },
];

export default function ReminderSettingsScreen({ navigation }) {
  const [enabled, setEnabled] = useState(false);
  const [selectedDay, setSelectedDay] = useState(2);
  const [selectedHour, setSelectedHour] = useState(8);
  const [studentName, setStudentName] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const settings = await AsyncStorage.getItem('reminder_settings');
      if (settings) {
        const s = JSON.parse(settings);
        setEnabled(s.enabled || false);
        setSelectedDay(s.day || 2);
        setSelectedHour(s.hour || 8);
      }
      const userData = await AsyncStorage.getItem('user_data');
      if (userData) {
        const u = JSON.parse(userData);
        setStudentName(u.full_name || '');
      }
    } catch (e) {
      console.log('Load settings error:', e.message);
    }
  };

  const requestPermission = async () => {
    const { status: existing } = await Notifications.getPermissionsAsync();
    if (existing === 'granted') return true;
    const { status } = await Notifications.requestPermissionsAsync();
    return status === 'granted';
  };

  const scheduleReminder = async () => {
    const hasPermission = await requestPermission();
    if (!hasPermission) {
      Alert.alert(
        'Permission Required',
        'Please enable notifications in your phone settings to use reminders.',
        [{ text: 'OK' }]
      );
      return false;
    }

    await Notifications.cancelAllScheduledNotificationsAsync();

    if (enabled) {
      await Notifications.scheduleNotificationAsync({
        content: {
          title: 'Top Up Reminder',
          body: `Don't forget to top up ${studentName}'s meal account before the week starts!`,
          sound: true,
        },
        trigger: {
          type: Notifications.SchedulableTriggerInputTypes.WEEKLY,
          weekday: selectedDay,
          hour: selectedHour,
          minute: 0,
        },
      });
    }

    await AsyncStorage.setItem(
      'reminder_settings',
      JSON.stringify({ enabled, day: selectedDay, hour: selectedHour })
    );
    return true;
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const ok = await scheduleReminder();
      if (ok) {
        Alert.alert(
          'Saved',
          enabled
            ? `Reminder set for ${REMINDER_DAYS.find(d => d.value === selectedDay)?.label} at ${REMINDER_TIMES.find(t => t.hour === selectedHour)?.label}`
            : 'Reminders disabled.',
          [{ text: 'OK', onPress: () => navigation.goBack() }]
        );
      }
    } catch (e) {
      Alert.alert('Error', 'Could not save reminder.');
    } finally {
      setSaving(false);
    }
  };

  const dayName = REMINDER_DAYS.find(d => d.value === selectedDay)?.label;
  const timeName = REMINDER_TIMES.find(t => t.hour === selectedHour)?.label;

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Feather name="arrow-left" size={22} color="#A8D8C0" />
        </TouchableOpacity>
        <Text style={styles.title}>Top Up Reminders</Text>
        <View style={{ width: 22 }} />
      </View>

      <View style={styles.content}>
        <View style={styles.toggleCard}>
          <View style={{ flex: 1 }}>
            <Text style={styles.toggleTitle}>Weekly Reminder</Text>
            <Text style={styles.toggleSub}>Get reminded to top up every week</Text>
          </View>
          <Switch
            value={enabled}
            onValueChange={setEnabled}
            trackColor={{ false: '#E5E7EB', true: '#A7F3D0' }}
            thumbColor={enabled ? '#1A6E3C' : '#9CA3AF'}
          />
        </View>

        {enabled && (
          <>
            <Text style={styles.sectionTitle}>Reminder Day</Text>
            <View style={styles.optionsGrid}>
              {REMINDER_DAYS.map(d => (
                <TouchableOpacity
                  key={d.value}
                  style={[styles.optionBtn, selectedDay === d.value && styles.optionBtnActive]}
                  onPress={() => setSelectedDay(d.value)}
                >
                  <Text style={[
                    styles.optionBtnText, selectedDay === d.value && styles.optionBtnTextActive
                  ]}>
                    {d.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <Text style={styles.sectionTitle}>Reminder Time</Text>
            <View style={styles.optionsGrid}>
              {REMINDER_TIMES.map(t => (
                <TouchableOpacity
                  key={t.hour}
                  style={[styles.optionBtn, selectedHour === t.hour && styles.optionBtnActive]}
                  onPress={() => setSelectedHour(t.hour)}
                >
                  <Text style={[
                    styles.optionBtnText, selectedHour === t.hour && styles.optionBtnTextActive
                  ]}>
                    {t.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <View style={styles.previewCard}>
              <Feather name="bell" size={28} color="#3A4AB0" style={{ marginBottom: 8 }} />
              <Text style={styles.previewTitle}>Reminder Preview</Text>
              <Text style={styles.previewText}>Every {dayName} at {timeName}</Text>
              <Text style={styles.previewBody}>
                "Don't forget to top up {studentName}'s meal account!"
              </Text>
            </View>
          </>
        )}

        <TouchableOpacity
          style={[styles.saveBtn, saving && styles.saveBtnDisabled]}
          onPress={handleSave}
          disabled={saving}
        >
          <Text style={styles.saveBtnText}>{saving ? 'Saving...' : 'Save Reminder'}</Text>
        </TouchableOpacity>
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
  toggleCard: {
    backgroundColor: '#fff', borderRadius: 16, padding: 20,
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    marginBottom: 24, shadowColor: '#000', shadowOpacity: 0.04,
    shadowRadius: 6, elevation: 2,
  },
  toggleTitle: { fontSize: 16, fontWeight: '700', color: '#1A3A5C' },
  toggleSub: { fontSize: 12, color: '#6B7280', marginTop: 4 },
  sectionTitle: { fontSize: 14, fontWeight: '700', color: '#1A3A5C', marginBottom: 10 },
  optionsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 20 },
  optionBtn: {
    borderWidth: 1, borderColor: '#E5E7EB', borderRadius: 8,
    paddingVertical: 10, paddingHorizontal: 14, backgroundColor: '#fff',
  },
  optionBtnActive: { backgroundColor: '#1A3A5C', borderColor: '#1A3A5C' },
  optionBtnText: { fontSize: 13, fontWeight: '600', color: '#374151' },
  optionBtnTextActive: { color: '#fff' },
  previewCard: {
    backgroundColor: '#EEF0FB', borderRadius: 16, padding: 20,
    alignItems: 'center', marginBottom: 24,
  },
  previewTitle: { fontSize: 14, fontWeight: '700', color: '#3A4AB0', marginBottom: 4 },
  previewText: { fontSize: 13, color: '#374151', marginBottom: 8, fontWeight: '600' },
  previewBody: { fontSize: 13, color: '#6B7280', textAlign: 'center', fontStyle: 'italic' },
  saveBtn: { backgroundColor: '#1A6E3C', borderRadius: 12, paddingVertical: 15, alignItems: 'center' },
  saveBtnDisabled: { opacity: 0.6 },
  saveBtnText: { color: '#fff', fontSize: 15, fontWeight: '700' },
});
