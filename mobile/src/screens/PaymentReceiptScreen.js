import React, { useRef, useEffect } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet,
  Share, ScrollView, Animated
} from 'react-native';
import { Feather } from '@expo/vector-icons';

export default function PaymentReceiptScreen({ route, navigation }) {
  const {
    amount_ksh,
    new_balance_ksh,
    mpesa_reference,
    student_name,
    school_name,
    timestamp,
  } = route.params || {};

  const scaleAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.spring(scaleAnim, {
      toValue: 1, tension: 60, friction: 6, useNativeDriver: true,
    }).start();
  }, []);

  const handleShare = async () => {
    const receiptText = `
MEAL BALANCE RECEIPT
=======================
School: ${school_name}
Student: ${student_name}
Date: ${new Date(timestamp).toLocaleString('en-KE')}

Amount Paid: KES ${Number(amount_ksh).toLocaleString('en-KE', { minimumFractionDigits: 2 })}
M-Pesa Ref: ${mpesa_reference || '-'}
New Balance: KES ${Number(new_balance_ksh).toLocaleString('en-KE', { minimumFractionDigits: 2 })}

Smart School Feeding System
Webmasters Kenya
    `.trim();

    try {
      await Share.share({ message: receiptText, title: 'Meal Balance Receipt' });
    } catch (e) {
      console.log('Share error:', e.message);
    }
  };

  const rows = [
    { label: 'Student', value: student_name },
    { label: 'School', value: school_name },
    { label: 'Date & Time',
      value: new Date(timestamp || Date.now()).toLocaleString('en-KE', {
        day: 'numeric', month: 'long', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
      }) },
    { label: 'M-Pesa Reference', value: mpesa_reference || '—', mono: true },
    { label: 'Payment Method', value: 'M-Pesa (Lipa Na M-Pesa)' },
  ];

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Animated.View style={[styles.successCircle, { transform: [{ scale: scaleAnim }] }]}>
        <Feather name="check" size={40} color="#fff" />
      </Animated.View>

      <Text style={styles.successTitle}>Payment Successful</Text>
      <Text style={styles.successSub}>Your receipt is below</Text>

      <View style={styles.receipt}>
        <View style={styles.receiptHeader}>
          <View style={styles.receiptSchoolRow}>
            <Feather name="home" size={13} color="#1A3A5C" />
            <Text style={styles.receiptSchool}>{school_name}</Text>
          </View>
          <Text style={styles.receiptLabel}>PAYMENT RECEIPT</Text>
        </View>

        <View style={styles.amountSection}>
          <Text style={styles.amountLabel}>Amount Paid</Text>
          <Text style={styles.amountValue}>
            KES {Number(amount_ksh).toLocaleString('en-KE', { minimumFractionDigits: 2 })}
          </Text>
        </View>

        <View style={styles.divider} />

        {rows.map(row => (
          <View key={row.label} style={styles.receiptRow}>
            <Text style={styles.receiptRowLabel}>{row.label}</Text>
            <Text style={[styles.receiptRowValue, row.mono && styles.mono]}>
              {row.value}
            </Text>
          </View>
        ))}

        <View style={styles.divider} />

        <View style={styles.newBalanceSection}>
          <Text style={styles.newBalanceLabel}>New Meal Balance</Text>
          <Text style={styles.newBalanceValue}>
            KES {Number(new_balance_ksh).toLocaleString('en-KE', { minimumFractionDigits: 2 })}
          </Text>
        </View>

        <Text style={styles.receiptFooter}>
          Powered by Smart School Feeding System{'\n'}Webmasters Kenya
        </Text>
      </View>

      <TouchableOpacity style={styles.shareBtn} onPress={handleShare}>
        <Feather name="share-2" size={16} color="#fff" />
        <Text style={styles.shareBtnText}>Share Receipt</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.homeBtn} onPress={() => navigation.navigate('Home')}>
        <Text style={styles.homeBtnText}>Back to Home</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F7F9FC' },
  content: { padding: 24, alignItems: 'center', paddingBottom: 48 },
  successCircle: {
    width: 80, height: 80, borderRadius: 40, backgroundColor: '#1A6E3C',
    alignItems: 'center', justifyContent: 'center', marginTop: 16, marginBottom: 12,
    shadowColor: '#1A6E3C', shadowOpacity: 0.3, shadowRadius: 12, elevation: 6,
  },
  successTitle: { fontSize: 24, fontWeight: '700', color: '#1A3A5C', marginBottom: 4 },
  successSub: { fontSize: 14, color: '#6B7280', marginBottom: 24 },
  receipt: {
    width: '100%', backgroundColor: '#fff', borderRadius: 16, padding: 24,
    shadowColor: '#000', shadowOpacity: 0.08, shadowRadius: 16, elevation: 4,
    marginBottom: 20,
  },
  receiptHeader: { alignItems: 'center', marginBottom: 20 },
  receiptSchoolRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 4 },
  receiptSchool: { fontSize: 14, fontWeight: '700', color: '#1A3A5C' },
  receiptLabel: { fontSize: 11, color: '#9CA3AF', letterSpacing: 2, fontWeight: '600' },
  amountSection: { alignItems: 'center', marginBottom: 20 },
  amountLabel: { fontSize: 13, color: '#6B7280' },
  amountValue: { fontSize: 36, fontWeight: '700', color: '#1A6E3C', marginTop: 4 },
  divider: { borderTopWidth: 1, borderTopColor: '#F3F4F6', borderStyle: 'dashed', marginVertical: 16 },
  receiptRow: {
    flexDirection: 'row', justifyContent: 'space-between',
    alignItems: 'flex-start', marginBottom: 12,
  },
  receiptRowLabel: { fontSize: 12, color: '#9CA3AF', flex: 1 },
  receiptRowValue: {
    fontSize: 13, color: '#1A3A5C', fontWeight: '600', flex: 1, textAlign: 'right',
  },
  mono: { fontFamily: 'monospace', fontSize: 11 },
  newBalanceSection: { alignItems: 'center', marginTop: 4 },
  newBalanceLabel: { fontSize: 12, color: '#6B7280' },
  newBalanceValue: { fontSize: 22, fontWeight: '700', color: '#1A3A5C', marginTop: 4 },
  receiptFooter: {
    textAlign: 'center', fontSize: 10, color: '#9CA3AF',
    marginTop: 20, lineHeight: 16,
  },
  shareBtn: {
    width: '100%', backgroundColor: '#1A3A5C', borderRadius: 12,
    paddingVertical: 15, alignItems: 'center', marginBottom: 12,
    flexDirection: 'row', justifyContent: 'center', gap: 8,
  },
  shareBtnText: { color: '#fff', fontSize: 15, fontWeight: '700' },
  homeBtn: {
    width: '100%', borderWidth: 1, borderColor: '#E5E7EB', borderRadius: 12,
    paddingVertical: 15, alignItems: 'center', backgroundColor: '#fff',
  },
  homeBtnText: { color: '#374151', fontSize: 14, fontWeight: '600' },
});
