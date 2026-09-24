import React, { useState, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  Alert, ActivityIndicator, ScrollView, FlatList, RefreshControl
} from 'react-native';
import { Feather } from '@expo/vector-icons';
import { paymentsAPI } from '../services/api';

const STATUS_META = {
  pending: { color: '#D07020', bg: '#FEF3C7', label: 'Pending' },
  approved: { color: '#1A6E3C', bg: '#D1FAE5', label: 'Approved' },
  rejected: { color: '#C0392B', bg: '#FEE2E2', label: 'Rejected' },
};

export default function ApplyCreditScreen({ navigation }) {
  const [amount, setAmount] = useState('');
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    try {
      const res = await paymentsAPI.myCreditRequests();
      setRequests(res.data);
    } catch (e) {
      console.log('Credit requests error:', e.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleSubmit = async () => {
    const ksh = parseFloat(amount);
    if (isNaN(ksh) || ksh < 50) {
      Alert.alert('Error', 'Please enter an amount of at least KES 50.');
      return;
    }
    if (ksh > 5000) {
      Alert.alert('Error', 'Maximum requestable credit limit is KES 5,000.');
      return;
    }
    setSubmitting(true);
    try {
      await paymentsAPI.applyCredit({
        requested_amount_cents: Math.round(ksh * 100),
        reason: reason.trim(),
      });
      setAmount('');
      setReason('');
      Alert.alert('Request submitted', 'The school admin will review your request.');
      load();
    } catch (e) {
      Alert.alert('Could not submit', e.response?.data?.error || 'Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const renderRequest = ({ item }) => {
    const meta = STATUS_META[item.status] || STATUS_META.pending;
    return (
      <View style={styles.reqCard}>
        <View style={styles.reqTop}>
          <Text style={styles.reqAmount}>KES {item.requested_amount_ksh.toFixed(2)}</Text>
          <View style={[styles.badge, { backgroundColor: meta.bg }]}>
            <Text style={[styles.badgeText, { color: meta.color }]}>{meta.label}</Text>
          </View>
        </View>
        {item.reason ? <Text style={styles.reqReason}>{item.reason}</Text> : null}
        <Text style={styles.reqDate}>
          {new Date(item.created_at).toLocaleDateString('en-KE', {
            day: 'numeric', month: 'short', year: 'numeric'
          })}
        </Text>
      </View>
    );
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} />}
    >
      <TouchableOpacity onPress={() => navigation.goBack()} style={styles.back}>
        <Feather name="arrow-left" size={14} color="#1A6E3C" />
        <Text style={styles.backText}>Back</Text>
      </TouchableOpacity>

      <Text style={styles.title}>Apply for Credit</Text>
      <Text style={styles.subtitle}>
        Request a higher spending limit so your child can keep eating on credit —
        approval raises the limit, it doesn't add real balance. Pay it off later with a top-up.
      </Text>

      <Text style={styles.label}>Requested limit (KES, max 5,000)</Text>
      <TextInput
        style={styles.input}
        placeholder="e.g. 300"
        placeholderTextColor="#9CA3AF"
        value={amount}
        onChangeText={setAmount}
        keyboardType="numeric"
      />

      <Text style={styles.label}>Reason (optional)</Text>
      <TextInput
        style={[styles.input, styles.textarea]}
        placeholder="Why do you need this?"
        placeholderTextColor="#9CA3AF"
        value={reason}
        onChangeText={setReason}
        multiline
        numberOfLines={3}
      />

      <TouchableOpacity
        style={[styles.submitBtn, submitting && styles.submitBtnDisabled]}
        onPress={handleSubmit}
        disabled={submitting}
      >
        {submitting
          ? <ActivityIndicator color="#fff" />
          : <Text style={styles.submitBtnText}>Submit Request</Text>
        }
      </TouchableOpacity>

      <Text style={styles.sectionTitle}>Your Requests</Text>
      {loading ? (
        <ActivityIndicator size="large" color="#1A6E3C" style={{ marginTop: 20 }} />
      ) : (
        <FlatList
          data={requests}
          keyExtractor={item => String(item.id)}
          renderItem={renderRequest}
          scrollEnabled={false}
          ListEmptyComponent={
            <Text style={styles.emptyText}>You haven't requested credit yet.</Text>
          }
        />
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F7F9FC' },
  content: { padding: 24, paddingBottom: 48 },
  back: { marginBottom: 16, flexDirection: 'row', alignItems: 'center', gap: 6 },
  backText: { color: '#1A6E3C', fontSize: 14, fontWeight: '600' },
  title: { fontSize: 24, fontWeight: '700', color: '#1A3A5C', marginBottom: 4 },
  subtitle: { fontSize: 13, color: '#6B7280', marginBottom: 20, lineHeight: 18 },
  label: { fontSize: 13, fontWeight: '600', color: '#374151',
           marginBottom: 8, marginTop: 16 },
  input: { borderWidth: 1, borderColor: '#E5E7EB', borderRadius: 10,
           paddingHorizontal: 14, paddingVertical: 12, fontSize: 14,
           color: '#111827', backgroundColor: '#fff' },
  textarea: { height: 80, textAlignVertical: 'top' },
  submitBtn: { backgroundColor: '#1A6E3C', borderRadius: 10, paddingVertical: 16,
               alignItems: 'center', marginTop: 24 },
  submitBtnDisabled: { opacity: 0.6 },
  submitBtnText: { color: '#fff', fontSize: 15, fontWeight: '700' },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: '#1A3A5C',
                  marginTop: 32, marginBottom: 12 },
  reqCard: { backgroundColor: '#fff', borderRadius: 12, padding: 16,
             marginBottom: 10, shadowColor: '#000', shadowOpacity: 0.04,
             shadowRadius: 6, elevation: 2 },
  reqTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  reqAmount: { fontSize: 15, fontWeight: '700', color: '#1A3A5C' },
  badge: { borderRadius: 10, paddingHorizontal: 8, paddingVertical: 3 },
  badgeText: { fontSize: 10, fontWeight: '700' },
  reqReason: { fontSize: 12, color: '#6B7280', marginTop: 6 },
  reqDate: { fontSize: 11, color: '#9CA3AF', marginTop: 8 },
  emptyText: { fontSize: 13, color: '#9CA3AF', textAlign: 'center', marginTop: 20 },
});
