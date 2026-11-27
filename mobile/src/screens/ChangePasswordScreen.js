import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, ScrollView,
  Alert, ActivityIndicator
} from 'react-native';
import { Feather } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { authAPI } from '../services/api';

// Accounts are created by the school, so the first password is one the
// school administrator chose. This screen lets any user replace it. A
// successful change signs out every other device; this one gets new tokens.
export default function ChangePasswordScreen({ navigation }) {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!current || !next) {
      setErrors({ form: 'Enter your current password and a new password.' });
      return;
    }
    if (next !== confirm) {
      setErrors({ confirm: 'The new passwords do not match.' });
      return;
    }
    setErrors({});
    setSaving(true);
    try {
      const res = await authAPI.changePassword({
        current_password: current, new_password: next,
      });
      const { tokens } = res.data;
      await AsyncStorage.setItem('access_token', tokens.access);
      await AsyncStorage.setItem('refresh_token', tokens.refresh);
      Alert.alert('Password changed',
        'Your password has been changed and you have been signed out on your other devices.',
        [{ text: 'OK', onPress: () => navigation.goBack() }]);
    } catch (e) {
      const data = e.response?.data || {};
      setErrors({
        current: data.current_password?.[0],
        next: (data.new_password || []).join(' '),
        form: !data.current_password && !data.new_password
          ? 'Could not change your password. Please try again.' : undefined,
      });
    } finally {
      setSaving(false);
    }
  };

  const field = (label, value, onChange, error) => (
    <>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        style={[styles.input, error && styles.inputError]}
        value={value}
        onChangeText={onChange}
        secureTextEntry
        autoCapitalize="none"
        autoCorrect={false}
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}
    </>
  );

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <TouchableOpacity onPress={() => navigation.goBack()} style={styles.back}>
        <Feather name="arrow-left" size={14} color="#1A6E3C" />
        <Text style={styles.backText}>Back</Text>
      </TouchableOpacity>

      <Text style={styles.title}>Change Password</Text>
      <Text style={styles.subtitle}>
        Your school set your first password. Choose a new one that only you know.
      </Text>

      {field('Current password', current, setCurrent, errors.current)}
      {field('New password', next, setNext, errors.next)}
      {field('Confirm new password', confirm, setConfirm, errors.confirm)}

      <Text style={styles.hint}>
        Use at least 8 characters. Avoid common words, only numbers, or your name.
      </Text>
      {errors.form ? <Text style={styles.error}>{errors.form}</Text> : null}

      <TouchableOpacity
        style={[styles.submitBtn, saving && styles.submitBtnDisabled]}
        onPress={handleSave}
        disabled={saving}
      >
        {saving
          ? <ActivityIndicator color="#fff" />
          : <Text style={styles.submitBtnText}>Change Password</Text>}
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F7F9FC' },
  content: { padding: 24, paddingTop: 56, paddingBottom: 48 },
  back: { marginBottom: 16, flexDirection: 'row', alignItems: 'center', gap: 6 },
  backText: { color: '#1A6E3C', fontSize: 14, fontWeight: '600' },
  title: { fontSize: 24, fontWeight: '700', color: '#1A3A5C', marginBottom: 4 },
  subtitle: { fontSize: 13, color: '#6B7280', marginBottom: 12 },
  label: { fontSize: 13, fontWeight: '600', color: '#374151', marginBottom: 8, marginTop: 16 },
  input: { borderWidth: 1, borderColor: '#E5E7EB', borderRadius: 10,
           paddingHorizontal: 14, paddingVertical: 12, fontSize: 14,
           color: '#111827', backgroundColor: '#fff' },
  inputError: { borderColor: '#EF4444' },
  error: { color: '#C0392B', fontSize: 12, marginTop: 6 },
  hint: { fontSize: 12, color: '#6B7280', marginTop: 14 },
  submitBtn: { backgroundColor: '#1A6E3C', borderRadius: 10, paddingVertical: 16,
               alignItems: 'center', marginTop: 24 },
  submitBtnDisabled: { opacity: 0.6 },
  submitBtnText: { color: '#fff', fontSize: 15, fontWeight: '700' },
});
