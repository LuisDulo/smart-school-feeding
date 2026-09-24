import React, { useState, useEffect } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet,
  Modal, FlatList, ActivityIndicator
} from 'react-native';
import { Feather } from '@expo/vector-icons';
import { useAuth } from '../context/AuthContext';
import { paymentsAPI } from '../services/api';

// A student has no linked children of their own — only parents do
// (see MyChildrenView, which 403s for any other role).
export default function ChildSelector({ selectedChild, onSelectChild }) {
  const { user } = useAuth();
  const [children, setChildren] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user?.role !== 'parent') return;
    loadChildren();
  }, [user?.role]);

  const loadChildren = async () => {
    setLoading(true);
    try {
      const res = await paymentsAPI.myChildren();
      setChildren(res.data);
      if (res.data.length > 0 && !selectedChild) {
        onSelectChild(res.data[0]);
      }
    } catch (e) {
      console.log('Children load error:', e.message);
    } finally {
      setLoading(false);
    }
  };

  if (user?.role !== 'parent' || loading) return null;
  if (!children || children.length <= 1) return null;

  return (
    <>
      <TouchableOpacity
        style={styles.selector}
        onPress={() => setShowModal(true)}
      >
        <Text style={styles.selectorLabel}>Viewing:</Text>
        <Text style={styles.selectorName}>
          {selectedChild?.student_name || 'Select child'}
        </Text>
        <Feather name="chevron-down" size={14} color="#A8D8C0" />
      </TouchableOpacity>

      <Modal
        visible={showModal}
        transparent
        animationType="slide"
        onRequestClose={() => setShowModal(false)}
      >
        <TouchableOpacity
          style={styles.overlay}
          onPress={() => setShowModal(false)}
          activeOpacity={1}
        >
          <View style={styles.modal}>
            <Text style={styles.modalTitle}>Select Child</Text>
            <FlatList
              data={children}
              keyExtractor={c => String(c.id)}
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={[
                    styles.childRow,
                    selectedChild?.id === item.id && styles.childRowActive
                  ]}
                  onPress={() => {
                    onSelectChild(item);
                    setShowModal(false);
                  }}
                >
                  <View style={styles.childAvatar}>
                    <Text style={styles.childAvatarText}>
                      {item.student_name.charAt(0)}
                    </Text>
                  </View>
                  <View style={styles.childInfo}>
                    <Text style={styles.childName}>{item.student_name}</Text>
                    <View style={styles.childBalanceRow}>
                      <Text style={styles.childBalance}>
                        KES {item.balance_ksh?.toLocaleString(
                          'en-KE', { minimumFractionDigits: 2 })}
                      </Text>
                      {item.is_low && (
                        <View style={styles.lowBadge}>
                          <Feather name="alert-triangle" size={10} color="#D07020" />
                          <Text style={styles.lowBadgeText}>Low</Text>
                        </View>
                      )}
                    </View>
                  </View>
                  {selectedChild?.id === item.id && (
                    <Feather name="check" size={20} color="#1A6E3C" />
                  )}
                </TouchableOpacity>
              )}
            />
          </View>
        </TouchableOpacity>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  selector: {
    flexDirection: 'row', alignItems: 'center',
    gap: 6, paddingVertical: 6, paddingHorizontal: 12,
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderRadius: 20, marginTop: 10, alignSelf: 'flex-start',
  },
  selectorLabel: { color: '#A8D8C0', fontSize: 12 },
  selectorName: { color: '#fff', fontSize: 13, fontWeight: '700' },
  overlay: {
    flex: 1, backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modal: {
    backgroundColor: '#fff', borderTopLeftRadius: 20,
    borderTopRightRadius: 20, padding: 24, maxHeight: '60%',
  },
  modalTitle: {
    fontSize: 18, fontWeight: '700', color: '#1A3A5C',
    marginBottom: 16, textAlign: 'center',
  },
  childRow: {
    flexDirection: 'row', alignItems: 'center',
    padding: 14, borderRadius: 12, marginBottom: 8,
    backgroundColor: '#F7F9FC',
  },
  childRowActive: { backgroundColor: '#D1FAE5' },
  childAvatar: {
    width: 44, height: 44, borderRadius: 22,
    backgroundColor: '#1A3A5C', alignItems: 'center',
    justifyContent: 'center', marginRight: 12,
  },
  childAvatarText: { color: '#fff', fontSize: 18, fontWeight: '700' },
  childInfo: { flex: 1 },
  childName: { fontSize: 15, fontWeight: '700', color: '#1A3A5C' },
  childBalanceRow: {
    flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 2,
  },
  childBalance: { fontSize: 13, color: '#6B7280' },
  lowBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 3,
    backgroundColor: '#FEF3C7', borderRadius: 8,
    paddingHorizontal: 6, paddingVertical: 2,
  },
  lowBadgeText: { fontSize: 10, color: '#D07020', fontWeight: '700' },
});
