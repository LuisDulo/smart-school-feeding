import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  Alert, ActivityIndicator, ScrollView
} from 'react-native';
import { paymentsAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';

const PRESET_AMOUNTS = [
  { label: 'KES 100', cents: 10000 },
  { label: 'KES 200', cents: 20000 },
  { label: 'KES 500', cents: 50000 },
  { label: 'KES 1,000', cents: 100000 },
];

export default function TopUpScreen({ navigation }) {
  const { user } = useAuth();
  const [selectedAmount, setSelectedAmount] = useState(null);
  const [customAmount, setCustomAmount] = useState('');
  const [phone, setPhone] = useState('');
  const [loading, setLoading] = useState(false);

  const getAmountCents = () => {
    if (selectedAmount) return selectedAmount;
    const ksh = parseFloat(customAmount);
    if (!isNaN(ksh) && ksh >= 100) return Math.round(ksh * 100);
    return null;
  };

  const handlePay = async () => {
    const amountCents = getAmountCents();
    if (!amountCents) {
      Alert.alert('Error', 'Please select or enter a valid amount (minimum KES 100).');
      return;
    }
    if (!phone || phone.length < 9) {
      Alert.alert('Error', 'Please enter a valid M-Pesa phone number.');
      return;
    }

    setLoading(true);
    try {
      const response = await paymentsAPI.initiate({
        amount_cents: amountCents,
        phone_number: phone,
      });

      const { transaction_id, checkout_request_id } = response.data;

      Alert.alert(
        'M-Pesa PIN Prompt Sent',
        `Check your phone (${phone}) for an M-Pesa PIN prompt and enter your PIN to confirm.`,
        [{ text: 'OK', onPress: () =>
          navigation.navigate('PaymentStatus', {
            transaction_id,
            checkout_request_id,
            amount_ksh: amountCents / 100
          })
        }]
      );
    } catch (error) {
      const msg = error.response?.data?.error || 'Payment failed. Please try again.';
      Alert.alert('Payment Failed', msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <TouchableOpacity onPress={() => navigation.goBack()} style={styles.back}>
        <Text style={styles.backText}>← Back</Text>
      </TouchableOpacity>

      <Text style={styles.title}>Top Up Meal Balance</Text>
      <Text style={styles.subtitle}>Funds go directly to the school meal account</Text>

      <Text style={styles.label}>Select amount</Text>
      <View style={styles.amountGrid}>
        {PRESET_AMOUNTS.map(a => (
          <TouchableOpacity
            key={a.cents}
            style={[styles.amountBtn,
              selectedAmount === a.cents && styles.amountBtnActive]}
            onPress={() => { setSelectedAmount(a.cents); setCustomAmount(''); }}
          >
            <Text style={[styles.amountBtnText,
              selectedAmount === a.cents && styles.amountBtnTextActive]}>
              {a.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text style={styles.label}>Or enter custom amount (KES)</Text>
      <TextInput
        style={styles.input}
        placeholder="e.g. 750"
        placeholderTextColor="#9CA3AF"
        value={customAmount}
        onChangeText={v => { setCustomAmount(v); setSelectedAmount(null); }}
        keyboardType="numeric"
      />

      <Text style={styles.label}>M-Pesa phone number</Text>
      <TextInput
        style={styles.input}
        placeholder="0712 345 678"
        placeholderTextColor="#9CA3AF"
        value={phone}
        onChangeText={setPhone}
        keyboardType="phone-pad"
      />

      <View style={styles.infoCard}>
        <Text style={styles.infoTitle}>ℹ️  How it works</Text>
        <Text style={styles.infoText}>
          Tap Pay below. You will receive an M-Pesa PIN prompt on your phone.
          Enter your PIN to confirm. Your meal balance updates instantly.
        </Text>
      </View>

      <TouchableOpacity
        style={[styles.payBtn, loading && styles.payBtnDisabled]}
        onPress={handlePay}
        disabled={loading}
      >
        {loading
          ? <ActivityIndicator color="#fff" />
          : <Text style={styles.payBtnText}>
              Pay KES {getAmountCents() ? (getAmountCents()/100).toFixed(0) : '—'} via M-Pesa
            </Text>
        }
      </TouchableOpacity>

      <Text style={styles.secured}>🔒 Secured by Safaricom Daraja API</Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F7F9FC' },
  content: { padding: 24, paddingBottom: 48 },
  back: { marginBottom: 16 },
  backText: { color: '#1A6E3C', fontSize: 14, fontWeight: '600' },
  title: { fontSize: 24, fontWeight: '700', color: '#1A3A5C', marginBottom: 4 },
  subtitle: { fontSize: 13, color: '#6B7280', marginBottom: 24 },
  label: { fontSize: 13, fontWeight: '600', color: '#374151',
           marginBottom: 8, marginTop: 16 },
  amountGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  amountBtn: { width: '47%', borderWidth: 1, borderColor: '#E5E7EB',
               borderRadius: 10, paddingVertical: 14, alignItems: 'center',
               backgroundColor: '#fff' },
  amountBtnActive: { backgroundColor: '#1A6E3C', borderColor: '#1A6E3C' },
  amountBtnText: { fontSize: 14, fontWeight: '600', color: '#374151' },
  amountBtnTextActive: { color: '#fff' },
  input: { borderWidth: 1, borderColor: '#E5E7EB', borderRadius: 10,
           paddingHorizontal: 14, paddingVertical: 12, fontSize: 14,
           color: '#111827', backgroundColor: '#fff' },
  infoCard: { backgroundColor: '#EEF0FB', borderRadius: 10, padding: 16,
              marginTop: 20, borderWidth: 1, borderColor: '#C7CDF0' },
  infoTitle: { fontSize: 13, fontWeight: '700', color: '#3A4AB0', marginBottom: 6 },
  infoText: { fontSize: 12, color: '#374151', lineHeight: 18 },
  payBtn: { backgroundColor: '#1A6E3C', borderRadius: 10, paddingVertical: 16,
            alignItems: 'center', marginTop: 24 },
  payBtnDisabled: { opacity: 0.6 },
  payBtnText: { color: '#fff', fontSize: 15, fontWeight: '700' },
  secured: { textAlign: 'center', marginTop: 16, fontSize: 11, color: '#9CA3AF' },
});
