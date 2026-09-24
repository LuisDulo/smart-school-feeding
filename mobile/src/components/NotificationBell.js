import React, { useState, useEffect } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet,
  Modal, FlatList, ActivityIndicator
} from 'react-native';
import { Feather } from '@expo/vector-icons';
import { paymentsAPI } from '../services/api';

// Maps the backend's plain icon-name string (ActivityFeedView) to a
// Feather glyph — kept separate from the name itself so the backend
// doesn't need to know anything about React Native's icon library.
const ICONS = {
  'credit-card': 'credit-card',
  'coffee': 'coffee',
};

export default function NotificationBell({ mealAccountId }) {
  const [activities, setActivities] = useState([]);
  const [unread, setUnread] = useState(0);
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadActivity();
    const interval = setInterval(loadActivity, 60000);
    return () => clearInterval(interval);
  }, [mealAccountId]);

  const loadActivity = async () => {
    try {
      const res = await paymentsAPI.activity(mealAccountId);
      setActivities(res.data.activities);
      setUnread(res.data.unread_count);
    } catch (e) {
      console.log('Activity error:', e.message);
    }
  };

  const handleOpen = () => {
    setShowModal(true);
    setUnread(0);
  };

  const getRelativeTime = (timestamp) => {
    const diff = Date.now() - new Date(timestamp).getTime();
    const mins = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${days}d ago`;
  };

  return (
    <>
      <TouchableOpacity style={styles.bellBtn} onPress={handleOpen}>
        <Feather name="bell" size={22} color="#fff" />
        {unread > 0 && (
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{unread > 9 ? '9+' : unread}</Text>
          </View>
        )}
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
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Recent Activity</Text>
              <TouchableOpacity onPress={() => setShowModal(false)}>
                <Feather name="x" size={20} color="#6B7280" />
              </TouchableOpacity>
            </View>

            {loading ? (
              <ActivityIndicator color="#1A6E3C" style={{ marginTop: 20 }} />
            ) : activities.length === 0 ? (
              <Text style={styles.emptyText}>No recent activity</Text>
            ) : (
              <FlatList
                data={activities}
                keyExtractor={(_, i) => String(i)}
                renderItem={({ item }) => (
                  <View style={styles.activityItem}>
                    <View style={styles.activityIconWrap}>
                      <Feather
                        name={ICONS[item.icon] || 'activity'}
                        size={16}
                        color="#1A3A5C"
                      />
                    </View>
                    <View style={styles.activityContent}>
                      <Text style={styles.activityTitle}>{item.title}</Text>
                      <Text style={styles.activitySub}>{item.subtitle}</Text>
                    </View>
                    <View style={styles.activityRight}>
                      <Text style={styles.activityTime}>
                        {getRelativeTime(item.timestamp)}
                      </Text>
                      {item.amount_ksh !== undefined && (
                        <Text style={[
                          styles.activityAmount,
                          { color: item.amount_ksh > 0 ? '#1A6E3C' : '#C0392B' }
                        ]}>
                          {item.amount_ksh > 0 ? '+' : ''}
                          KES {Math.abs(item.amount_ksh).toFixed(0)}
                        </Text>
                      )}
                    </View>
                  </View>
                )}
              />
            )}
          </View>
        </TouchableOpacity>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  bellBtn: { position: 'relative', padding: 4 },
  badge: {
    position: 'absolute', top: 0, right: 0,
    backgroundColor: '#C0392B', borderRadius: 8,
    minWidth: 16, height: 16, alignItems: 'center',
    justifyContent: 'center', paddingHorizontal: 3,
  },
  badgeText: { color: '#fff', fontSize: 9, fontWeight: '700' },
  overlay: {
    flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end',
  },
  modal: {
    backgroundColor: '#fff', borderTopLeftRadius: 20,
    borderTopRightRadius: 20, padding: 20, maxHeight: '75%',
  },
  modalHeader: {
    flexDirection: 'row', justifyContent: 'space-between',
    alignItems: 'center', marginBottom: 16,
  },
  modalTitle: { fontSize: 18, fontWeight: '700', color: '#1A3A5C' },
  emptyText: { textAlign: 'center', color: '#9CA3AF', fontSize: 14, padding: 32 },
  activityItem: {
    flexDirection: 'row', alignItems: 'flex-start', paddingVertical: 12,
    borderBottomWidth: 1, borderBottomColor: '#F3F4F6', gap: 12,
  },
  activityIconWrap: {
    width: 32, height: 32, borderRadius: 16,
    backgroundColor: '#F7F9FC', alignItems: 'center', justifyContent: 'center',
  },
  activityContent: { flex: 1 },
  activityTitle: { fontSize: 13, fontWeight: '600', color: '#1A3A5C' },
  activitySub: { fontSize: 11, color: '#6B7280', marginTop: 2 },
  activityRight: { alignItems: 'flex-end' },
  activityTime: { fontSize: 10, color: '#9CA3AF' },
  activityAmount: { fontSize: 13, fontWeight: '700', marginTop: 4 },
});
