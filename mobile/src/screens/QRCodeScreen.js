import React, { useState, useEffect } from 'react';
import {
  View, Text, StyleSheet, ActivityIndicator,
  TouchableOpacity, Share, ScrollView
} from 'react-native';
import QRCode from 'react-native-qrcode-svg';
import { Feather, MaterialCommunityIcons } from '@expo/vector-icons';
import { mealsAPI } from '../services/api';

export default function QRCodeScreen({ navigation, route }) {
  const mealAccountId = route.params?.meal_account_id;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    loadQRData();
  }, []);

  const loadQRData = async () => {
    setLoading(true);
    setError(false);
    try {
      const res = await mealsAPI.qrData(mealAccountId);
      setData(res.data);
    } catch (e) {
      console.log('QR error:', e.message);
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  const handleShare = async () => {
    try {
      await Share.share({
        message:
          `${data.student_name}'s meal QR code - ${data.school_name}. ` +
          `Show this to kitchen staff to collect a meal.`,
        title: 'Student Meal QR Code',
      });
    } catch (e) {
      console.log('Share error:', e.message);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Feather name="arrow-left" size={22} color="#A8D8C0" />
        </TouchableOpacity>
        <Text style={styles.title}>Student QR Code</Text>
        <View style={{ width: 22 }} />
      </View>

      <View style={styles.body}>
        {loading ? (
          <ActivityIndicator color="#1A6E3C" size="large" style={{ marginTop: 60 }} />
        ) : data ? (
          <>
            <View style={styles.instructionCard}>
              <MaterialCommunityIcons name="cellphone-check" size={28} color="#3A4AB0" />
              <Text style={styles.instructionTitle}>How to use</Text>
              <Text style={styles.instructionText}>
                Show this QR code to kitchen staff when collecting a meal.
                They will scan it to record the meal and deduct from the balance.
              </Text>
            </View>

            <View style={styles.qrCard}>
              <View style={styles.schoolBadge}>
                <MaterialCommunityIcons name="school-outline" size={13} color="#1A3A5C" />
                <Text style={styles.schoolBadgeText}>{data.school_name}</Text>
              </View>

              <View style={styles.qrContainer}>
                <QRCode
                  value={data.qr_data}
                  size={220}
                  color="#1A3A5C"
                  backgroundColor="#fff"
                />
              </View>

              <View style={styles.studentInfo}>
                <Text style={styles.studentName}>{data.student_name}</Text>
                <Text style={styles.studentId}>ID: {data.student_id}</Text>
              </View>

              <View style={styles.balanceStrip}>
                <Text style={styles.balanceLabel}>Meal Balance</Text>
                <Text style={[
                  styles.balanceValue,
                  { color: data.balance_ksh < 100 ? '#C0392B' : '#1A6E3C' }
                ]}>
                  KES {data.balance_ksh?.toLocaleString(
                    'en-KE', { minimumFractionDigits: 2 })}
                </Text>
              </View>

              {data.balance_ksh < 100 && (
                <View style={styles.lowWarning}>
                  <Feather name="alert-triangle" size={13} color="#D07020" />
                  <Text style={styles.lowWarningText}>Low balance - please top up</Text>
                </View>
              )}
            </View>

            <TouchableOpacity style={styles.shareBtn} onPress={handleShare}>
              <Feather name="share-2" size={16} color="#fff" />
              <Text style={styles.shareBtnText}>Share QR Code</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.topUpBtn}
              onPress={() => navigation.navigate('TopUp')}
            >
              <Feather name="credit-card" size={16} color="#fff" />
              <Text style={styles.topUpBtnText}>Top Up Balance</Text>
            </TouchableOpacity>

            <View style={styles.noteCard}>
              <View style={styles.noteTitleRow}>
                <Feather name="lock" size={13} color="#1A3A5C" />
                <Text style={styles.noteTitle}>Security Note</Text>
              </View>
              <Text style={styles.noteText}>
                This QR code is uniquely linked to {data.student_name}'s meal
                account. Each scan deducts the meal cost and prevents
                double-serving the same student twice in one day.
              </Text>
            </View>
          </>
        ) : (
          <View style={styles.error}>
            <Text style={styles.errorText}>
              {error ? 'Could not load QR code' : 'No QR code available'}
            </Text>
            <TouchableOpacity style={styles.retryBtn} onPress={loadQRData}>
              <Text style={styles.retryBtnText}>Retry</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F7F9FC' },
  content: { paddingBottom: 40 },
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    backgroundColor: '#1A3A5C', paddingTop: 52, paddingBottom: 16, paddingHorizontal: 20,
  },
  title: { color: '#fff', fontSize: 18, fontWeight: '700' },
  body: { padding: 20 },
  instructionCard: {
    backgroundColor: '#EEF0FB', borderRadius: 16, padding: 16,
    alignItems: 'center', marginBottom: 20,
  },
  instructionTitle: {
    fontSize: 14, fontWeight: '700', color: '#3A4AB0', marginTop: 8, marginBottom: 6,
  },
  instructionText: { fontSize: 12, color: '#374151', textAlign: 'center', lineHeight: 18 },
  qrCard: {
    backgroundColor: '#fff', borderRadius: 20, padding: 24, alignItems: 'center',
    shadowColor: '#000', shadowOpacity: 0.08, shadowRadius: 16, elevation: 4,
    marginBottom: 16,
  },
  schoolBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    backgroundColor: '#F7F9FC', borderRadius: 20,
    paddingVertical: 6, paddingHorizontal: 16, marginBottom: 20,
  },
  schoolBadgeText: { fontSize: 12, fontWeight: '700', color: '#1A3A5C' },
  qrContainer: {
    padding: 12, backgroundColor: '#fff', borderRadius: 12,
    borderWidth: 1, borderColor: '#F3F4F6', marginBottom: 20,
  },
  studentInfo: { alignItems: 'center', marginBottom: 16 },
  studentName: { fontSize: 20, fontWeight: '700', color: '#1A3A5C' },
  studentId: { fontSize: 12, color: '#9CA3AF', marginTop: 4, fontFamily: 'monospace' },
  balanceStrip: {
    width: '100%', flexDirection: 'row', justifyContent: 'space-between',
    backgroundColor: '#F7F9FC', borderRadius: 10, padding: 12,
  },
  balanceLabel: { fontSize: 13, color: '#6B7280' },
  balanceValue: { fontSize: 15, fontWeight: '700' },
  lowWarning: {
    width: '100%', flexDirection: 'row', justifyContent: 'center',
    alignItems: 'center', gap: 6, backgroundColor: '#FEF3C7',
    borderRadius: 8, padding: 10, marginTop: 10,
  },
  lowWarningText: { fontSize: 12, color: '#D07020', fontWeight: '600' },
  shareBtn: {
    backgroundColor: '#1A3A5C', borderRadius: 12, paddingVertical: 14,
    alignItems: 'center', marginBottom: 10, marginHorizontal: 20,
    flexDirection: 'row', justifyContent: 'center', gap: 8,
  },
  shareBtnText: { color: '#fff', fontSize: 14, fontWeight: '700' },
  topUpBtn: {
    backgroundColor: '#1A6E3C', borderRadius: 12, paddingVertical: 14,
    alignItems: 'center', marginBottom: 16, marginHorizontal: 20,
    flexDirection: 'row', justifyContent: 'center', gap: 8,
  },
  topUpBtnText: { color: '#fff', fontSize: 14, fontWeight: '700' },
  noteCard: { backgroundColor: '#F7F9FC', borderRadius: 12, padding: 16, marginHorizontal: 20 },
  noteTitleRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 6 },
  noteTitle: { fontSize: 13, fontWeight: '700', color: '#1A3A5C' },
  noteText: { fontSize: 12, color: '#6B7280', lineHeight: 18 },
  error: { alignItems: 'center', paddingTop: 60 },
  errorText: { fontSize: 16, color: '#C0392B' },
  retryBtn: { backgroundColor: '#1A6E3C', borderRadius: 8, padding: 12, marginTop: 16 },
  retryBtnText: { color: '#fff', fontSize: 14, fontWeight: '700' },
});
