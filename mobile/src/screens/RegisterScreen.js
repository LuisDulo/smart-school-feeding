import React, { useState, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  Alert, ActivityIndicator, ScrollView
} from 'react-native';
import { Feather } from '@expo/vector-icons';
import { useAuth } from '../context/AuthContext';
import { authAPI } from '../services/api';

export default function RegisterScreen({ navigation }) {
  const { register } = useAuth();
  const [schools, setSchools] = useState([]);
  const [form, setForm] = useState({
    full_name: '', email: '', password: '',
    role: 'student', school_id: null
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    authAPI.getSchools()
      .then(r => setSchools(r.data))
      .catch(() => Alert.alert('Error', 'Could not load schools.'));
  }, []);

  const update = (key, val) => setForm(prev => ({ ...prev, [key]: val }));

  const handleRegister = async () => {
    const { full_name, email, password, role, school_id } = form;
    if (!full_name || !email || !password || !school_id) {
      Alert.alert('Error', 'Please fill in all fields.');
      return;
    }
    setLoading(true);
    try {
      await register({ full_name, email, password, role, school_id });
    } catch (error) {
      const errors = error.response?.data;
      const msg = typeof errors === 'object'
        ? Object.values(errors).flat().join('\n')
        : 'Registration failed.';
      Alert.alert('Registration Failed', msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <TouchableOpacity onPress={() => navigation.goBack()} style={styles.back}>
        <Feather name="arrow-left" size={14} color="#1A6E3C" />
        <Text style={styles.backText}>Back</Text>
      </TouchableOpacity>

      <Text style={styles.title}>Create Account</Text>
      <Text style={styles.subtitle}>Register to manage your child's meals</Text>

      {[
        { label: 'Full name', key: 'full_name', placeholder: 'John Kamau' },
        { label: 'Email address', key: 'email', placeholder: 'john@email.com', keyboard: 'email-address' },
        { label: 'Password', key: 'password', placeholder: '••••••••', secure: true },
      ].map(field => (
        <View key={field.key}>
          <Text style={styles.label}>{field.label}</Text>
          <TextInput
            style={styles.input}
            placeholder={field.placeholder}
            placeholderTextColor="#9CA3AF"
            value={form[field.key]}
            onChangeText={v => update(field.key, v)}
            keyboardType={field.keyboard || 'default'}
            autoCapitalize={field.key === 'email' ? 'none' : 'words'}
            secureTextEntry={!!field.secure}
          />
        </View>
      ))}

      <Text style={styles.label}>Role</Text>
      <View style={styles.roleRow}>
        {['parent', 'student'].map(r => (
          <TouchableOpacity
            key={r}
            style={[styles.roleBtn, form.role === r && styles.roleBtnActive]}
            onPress={() => update('role', r)}
          >
            <Text style={[styles.roleBtnText, form.role === r && styles.roleBtnTextActive]}>
              {r.charAt(0).toUpperCase() + r.slice(1)}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text style={styles.label}>School</Text>
      {schools.map(s => (
        <TouchableOpacity
          key={s.id}
          style={[styles.schoolBtn, form.school_id === s.id && styles.schoolBtnActive]}
          onPress={() => update('school_id', s.id)}
        >
          <Text style={[styles.schoolBtnText, form.school_id === s.id && styles.schoolBtnTextActive]}>
            {s.name}
          </Text>
        </TouchableOpacity>
      ))}

      <TouchableOpacity
        style={[styles.button, loading && styles.buttonDisabled]}
        onPress={handleRegister}
        disabled={loading}
      >
        {loading
          ? <ActivityIndicator color="#fff" />
          : <Text style={styles.buttonText}>Create Account</Text>
        }
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F7F9FC' },
  content: { padding: 24, paddingBottom: 48 },
  back: { marginBottom: 16, flexDirection: 'row', alignItems: 'center', gap: 6 },
  backText: { color: '#1A6E3C', fontSize: 14, fontWeight: '600' },
  title: { fontSize: 24, fontWeight: '700', color: '#1A3A5C', marginBottom: 4 },
  subtitle: { fontSize: 13, color: '#6B7280', marginBottom: 24 },
  label: { fontSize: 13, fontWeight: '600', color: '#374151', marginBottom: 6, marginTop: 14 },
  input: { borderWidth: 1, borderColor: '#E5E7EB', borderRadius: 10,
           paddingHorizontal: 14, paddingVertical: 12, fontSize: 14,
           color: '#111827', backgroundColor: '#fff' },
  roleRow: { flexDirection: 'row', gap: 12 },
  roleBtn: { flex: 1, borderWidth: 1, borderColor: '#E5E7EB', borderRadius: 10,
             paddingVertical: 12, alignItems: 'center', backgroundColor: '#fff' },
  roleBtnActive: { backgroundColor: '#1A6E3C', borderColor: '#1A6E3C' },
  roleBtnText: { fontSize: 13, fontWeight: '600', color: '#374151' },
  roleBtnTextActive: { color: '#fff' },
  schoolBtn: { borderWidth: 1, borderColor: '#E5E7EB', borderRadius: 10,
               paddingVertical: 12, paddingHorizontal: 14, marginTop: 8, backgroundColor: '#fff' },
  schoolBtnActive: { backgroundColor: '#1A6E3C', borderColor: '#1A6E3C' },
  schoolBtnText: { fontSize: 13, color: '#374151' },
  schoolBtnTextActive: { color: '#fff', fontWeight: '600' },
  button: { backgroundColor: '#1A6E3C', borderRadius: 10, paddingVertical: 14,
            alignItems: 'center', marginTop: 28 },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: '#fff', fontSize: 15, fontWeight: '700' },
});
