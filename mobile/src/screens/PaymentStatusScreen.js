import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, StyleSheet, ActivityIndicator,
  TouchableOpacity, Animated
} from 'react-native';
import { Feather } from '@expo/vector-icons';
import { paymentsAPI } from '../services/api';

export default function PaymentStatusScreen({ route, navigation }) {
  const { transaction_id, amount_ksh } = route.params;
  const [status, setStatus] = useState('pending');
  const [newBalance, setNewBalance] = useState(null);
  const [mpesaRef, setMpesaRef] = useState('');
  const [dots, setDots] = useState('.');
  const pollRef = useRef(null);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // Animate in
    Animated.timing(fadeAnim, {
      toValue: 1, duration: 400, useNativeDriver: true
    }).start();

    // Animate waiting dots
    const dotsInterval = setInterval(() => {
      setDots(d => d.length >= 3 ? '.' : d + '.');
    }, 500);

    // Poll every 3 seconds for up to 2 minutes
    let attempts = 0;
    pollRef.current = setInterval(async () => {
      attempts++;
      try {
        const res = await paymentsAPI.status(transaction_id);
        const { status: txStatus, new_balance_ksh, mpesa_reference } = res.data;

        if (txStatus === 'confirmed' || txStatus === 'failed') {
          setStatus(txStatus);
          setNewBalance(new_balance_ksh);
          setMpesaRef(mpesa_reference || '');
          clearInterval(pollRef.current);
          clearInterval(dotsInterval);
        }
      } catch (e) {
        console.log('Polling error:', e.message);
      }

      if (attempts >= 40) {
        clearInterval(pollRef.current);
        clearInterval(dotsInterval);
        setStatus('timeout');
      }
    }, 3000);

    return () => {
      clearInterval(pollRef.current);
      clearInterval(dotsInterval);
    };
  }, []);

  if (status === 'pending') {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" color="#1A6E3C" />
        <Text style={styles.waitTitle}>Waiting for payment{dots}</Text>
        <Text style={styles.waitSub}>
          Enter your M-Pesa PIN on your phone to confirm KES {amount_ksh}
        </Text>
        <Text style={styles.waitNote}>This may take up to 30 seconds</Text>
      </View>
    );
  }

  if (status === 'confirmed') {
    return (
      <Animated.View style={[styles.container, { opacity: fadeAnim }]}>
        <Feather name="check-circle" size={72} color="#1A6E3C" />
        <Text style={styles.successTitle}>Payment Successful!</Text>
        <Text style={styles.successSub}>
          Your meal balance has been updated
        </Text>

        <View style={styles.detailCard}>
          {[
            ['Amount paid', `KES ${amount_ksh}`],
            ['M-Pesa Ref', mpesaRef || '—'],
            ['New balance', `KES ${newBalance?.toFixed(2) || '—'}`],
          ].map(([label, value]) => (
            <View key={label} style={styles.detailRow}>
              <Text style={styles.detailLabel}>{label}</Text>
              <Text style={styles.detailValue}>{value}</Text>
            </View>
          ))}
        </View>

        <View style={styles.smsNoteRow}>
          <Feather name="smartphone" size={12} color="#1A6E3C" />
          <Text style={styles.smsNote}>
            SMS confirmation sent by Safaricom
          </Text>
        </View>

        <TouchableOpacity
          style={styles.homeBtn}
          onPress={() => navigation.navigate('Home')}
        >
          <Text style={styles.homeBtnText}>Back to Home</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.historyBtn}
          onPress={() => navigation.navigate('PaymentHistory')}
        >
          <Text style={styles.historyBtnText}>View Payment History</Text>
        </TouchableOpacity>
      </Animated.View>
    );
  }

  return (
    <View style={styles.container}>
      <Feather name="x-circle" size={72} color="#C0392B" />
      <Text style={styles.failTitle}>
        {status === 'timeout' ? 'Payment Timed Out' : 'Payment Failed'}
      </Text>
      <Text style={styles.failSub}>
        {status === 'timeout'
          ? 'We could not confirm your payment. Check your M-Pesa messages.'
          : 'The payment was cancelled or declined. No money was deducted.'}
      </Text>
      <TouchableOpacity
        style={styles.retryBtn}
        onPress={() => navigation.goBack()}
      >
        <Text style={styles.retryBtnText}>Try Again</Text>
      </TouchableOpacity>
      <TouchableOpacity
        onPress={() => navigation.navigate('Home')}
      >
        <Text style={styles.cancelText}>Back to Home</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F7F9FC', justifyContent: 'center',
               alignItems: 'center', padding: 24 },
  waitTitle: { fontSize: 20, fontWeight: '700', color: '#1A3A5C',
               marginTop: 20, textAlign: 'center' },
  waitSub: { fontSize: 14, color: '#6B7280', textAlign: 'center',
             marginTop: 8, lineHeight: 20 },
  waitNote: { fontSize: 12, color: '#9CA3AF', marginTop: 16 },
  successTitle: { fontSize: 24, fontWeight: '700', color: '#1A6E3C',
                  marginTop: 16, textAlign: 'center' },
  successSub: { fontSize: 14, color: '#6B7280', textAlign: 'center', marginTop: 8 },
  detailCard: { backgroundColor: '#fff', borderRadius: 12, padding: 20,
                width: '100%', marginTop: 24,
                shadowColor: '#000', shadowOpacity: 0.05,
                shadowRadius: 8, elevation: 2 },
  detailRow: { flexDirection: 'row', justifyContent: 'space-between',
               paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#F3F4F6' },
  detailLabel: { fontSize: 13, color: '#6B7280' },
  detailValue: { fontSize: 13, fontWeight: '700', color: '#1A3A5C' },
  smsNoteRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 16 },
  smsNote: { fontSize: 12, color: '#1A6E3C' },
  homeBtn: { backgroundColor: '#1A6E3C', borderRadius: 10, paddingVertical: 14,
             paddingHorizontal: 48, marginTop: 24 },
  homeBtnText: { color: '#fff', fontSize: 15, fontWeight: '700' },
  historyBtn: { borderWidth: 1, borderColor: '#E5E7EB', borderRadius: 10,
                paddingVertical: 14, paddingHorizontal: 48, marginTop: 12 },
  historyBtnText: { color: '#374151', fontSize: 14, fontWeight: '600' },
  failTitle: { fontSize: 22, fontWeight: '700', color: '#C0392B',
               marginTop: 16, textAlign: 'center' },
  failSub: { fontSize: 14, color: '#6B7280', textAlign: 'center',
             marginTop: 8, lineHeight: 20 },
  retryBtn: { backgroundColor: '#1A6E3C', borderRadius: 10, paddingVertical: 14,
              paddingHorizontal: 48, marginTop: 24 },
  retryBtnText: { color: '#fff', fontSize: 15, fontWeight: '700' },
  cancelText: { color: '#6B7280', fontSize: 14, marginTop: 16 },
});
