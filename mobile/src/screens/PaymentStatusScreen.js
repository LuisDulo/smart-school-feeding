import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, StyleSheet, ActivityIndicator, TouchableOpacity
} from 'react-native';
import { Feather } from '@expo/vector-icons';
import { paymentsAPI } from '../services/api';

export default function PaymentStatusScreen({ route, navigation }) {
  const { transaction_id, amount_ksh } = route.params;
  const [status, setStatus] = useState('pending');
  const [dots, setDots] = useState('.');
  const pollRef = useRef(null);

  useEffect(() => {
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
        const {
          status: txStatus, new_balance_ksh, mpesa_reference,
          student_name, school_name,
        } = res.data;

        if (txStatus === 'confirmed') {
          clearInterval(pollRef.current);
          clearInterval(dotsInterval);
          navigation.replace('PaymentReceipt', {
            amount_ksh,
            new_balance_ksh,
            mpesa_reference,
            student_name,
            school_name,
            timestamp: new Date().toISOString(),
          });
          return;
        }
        if (txStatus === 'failed') {
          setStatus(txStatus);
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
  failTitle: { fontSize: 22, fontWeight: '700', color: '#C0392B',
               marginTop: 16, textAlign: 'center' },
  failSub: { fontSize: 14, color: '#6B7280', textAlign: 'center',
             marginTop: 8, lineHeight: 20 },
  retryBtn: { backgroundColor: '#1A6E3C', borderRadius: 10, paddingVertical: 14,
              paddingHorizontal: 48, marginTop: 24 },
  retryBtnText: { color: '#fff', fontSize: 15, fontWeight: '700' },
  cancelText: { color: '#6B7280', fontSize: 14, marginTop: 16 },
});
