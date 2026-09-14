import React, { useState, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  Alert, ActivityIndicator, ScrollView, FlatList, RefreshControl
} from 'react-native';
import { Feather } from '@expo/vector-icons';
import { supportAPI } from '../services/api';

const CATEGORIES = [
  { key: 'balance', label: 'Balance / Payment' },
  { key: 'meal_quality', label: 'Meal Quality' },
  { key: 'technical', label: 'App / Technical' },
  { key: 'other', label: 'Other' },
];

const STATUS_META = {
  open: { color: '#C0392B', bg: '#FEE2E2', label: 'Open' },
  in_progress: { color: '#D07020', bg: '#FEF3C7', label: 'In Progress' },
  resolved: { color: '#1A6E3C', bg: '#D1FAE5', label: 'Resolved' },
};

export default function RaiseIssueScreen({ navigation }) {
  const [category, setCategory] = useState('other');
  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    try {
      const res = await supportAPI.myIssues();
      setIssues(res.data);
    } catch (e) {
      console.log('Issues error:', e.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleSubmit = async () => {
    if (!subject.trim() || !description.trim()) {
      Alert.alert('Error', 'Please enter a subject and description.');
      return;
    }
    setSubmitting(true);
    try {
      await supportAPI.raiseIssue({ category, subject: subject.trim(), description: description.trim() });
      setSubject('');
      setDescription('');
      setCategory('other');
      Alert.alert('Issue submitted', 'The school admin will follow up.');
      load();
    } catch (e) {
      Alert.alert('Could not submit', e.response?.data?.error || 'Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const renderIssue = ({ item }) => {
    const meta = STATUS_META[item.status] || STATUS_META.open;
    return (
      <View style={styles.issueCard}>
        <View style={styles.issueTop}>
          <Text style={styles.issueSubject}>{item.subject}</Text>
          <View style={[styles.badge, { backgroundColor: meta.bg }]}>
            <Text style={[styles.badgeText, { color: meta.color }]}>{meta.label}</Text>
          </View>
        </View>
        <Text style={styles.issueDesc} numberOfLines={2}>{item.description}</Text>
        {item.resolution_notes ? (
          <Text style={styles.issueNotes}>Reply: {item.resolution_notes}</Text>
        ) : null}
        <Text style={styles.issueDate}>
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

      <Text style={styles.title}>Raise an Issue</Text>
      <Text style={styles.subtitle}>Tell the school admin what's going on</Text>

      <Text style={styles.label}>Category</Text>
      <View style={styles.categoryGrid}>
        {CATEGORIES.map(c => (
          <TouchableOpacity
            key={c.key}
            style={[styles.categoryBtn, category === c.key && styles.categoryBtnActive]}
            onPress={() => setCategory(c.key)}
          >
            <Text style={[styles.categoryBtnText, category === c.key && styles.categoryBtnTextActive]}>
              {c.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text style={styles.label}>Subject</Text>
      <TextInput
        style={styles.input}
        placeholder="Short summary"
        placeholderTextColor="#9CA3AF"
        value={subject}
        onChangeText={setSubject}
      />

      <Text style={styles.label}>Description</Text>
      <TextInput
        style={[styles.input, styles.textarea]}
        placeholder="Describe the issue in detail..."
        placeholderTextColor="#9CA3AF"
        value={description}
        onChangeText={setDescription}
        multiline
        numberOfLines={4}
      />

      <TouchableOpacity
        style={[styles.submitBtn, submitting && styles.submitBtnDisabled]}
        onPress={handleSubmit}
        disabled={submitting}
      >
        {submitting
          ? <ActivityIndicator color="#fff" />
          : <Text style={styles.submitBtnText}>Submit Issue</Text>
        }
      </TouchableOpacity>

      <Text style={styles.sectionTitle}>Your Issues</Text>
      {loading ? (
        <ActivityIndicator size="large" color="#1A6E3C" style={{ marginTop: 20 }} />
      ) : (
        <FlatList
          data={issues}
          keyExtractor={item => String(item.id)}
          renderItem={renderIssue}
          scrollEnabled={false}
          ListEmptyComponent={
            <Text style={styles.emptyText}>You haven't raised any issues yet.</Text>
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
  subtitle: { fontSize: 13, color: '#6B7280', marginBottom: 20 },
  label: { fontSize: 13, fontWeight: '600', color: '#374151',
           marginBottom: 8, marginTop: 16 },
  categoryGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  categoryBtn: { borderWidth: 1, borderColor: '#E5E7EB', borderRadius: 20,
                 paddingVertical: 8, paddingHorizontal: 14, backgroundColor: '#fff' },
  categoryBtnActive: { backgroundColor: '#1A6E3C', borderColor: '#1A6E3C' },
  categoryBtnText: { fontSize: 12, fontWeight: '600', color: '#374151' },
  categoryBtnTextActive: { color: '#fff' },
  input: { borderWidth: 1, borderColor: '#E5E7EB', borderRadius: 10,
           paddingHorizontal: 14, paddingVertical: 12, fontSize: 14,
           color: '#111827', backgroundColor: '#fff' },
  textarea: { height: 100, textAlignVertical: 'top' },
  submitBtn: { backgroundColor: '#1A6E3C', borderRadius: 10, paddingVertical: 16,
               alignItems: 'center', marginTop: 24 },
  submitBtnDisabled: { opacity: 0.6 },
  submitBtnText: { color: '#fff', fontSize: 15, fontWeight: '700' },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: '#1A3A5C',
                  marginTop: 32, marginBottom: 12 },
  issueCard: { backgroundColor: '#fff', borderRadius: 12, padding: 16,
               marginBottom: 10, shadowColor: '#000', shadowOpacity: 0.04,
               shadowRadius: 6, elevation: 2 },
  issueTop: { flexDirection: 'row', justifyContent: 'space-between',
              alignItems: 'flex-start', gap: 8 },
  issueSubject: { fontSize: 14, fontWeight: '700', color: '#1A3A5C', flex: 1 },
  badge: { borderRadius: 10, paddingHorizontal: 8, paddingVertical: 3 },
  badgeText: { fontSize: 10, fontWeight: '700' },
  issueDesc: { fontSize: 12, color: '#6B7280', marginTop: 6 },
  issueNotes: { fontSize: 12, color: '#1A6E3C', marginTop: 6, fontStyle: 'italic' },
  issueDate: { fontSize: 11, color: '#9CA3AF', marginTop: 8 },
  emptyText: { fontSize: 13, color: '#9CA3AF', textAlign: 'center', marginTop: 20 },
});
