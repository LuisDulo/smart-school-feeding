import React, { useState, useEffect, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Animated } from 'react-native';
import { Feather, MaterialCommunityIcons } from '@expo/vector-icons';
import { paymentsAPI } from '../services/api';

export default function RiskAlertBanner({ navigation, mealAccountId }) {
  const [riskData, setRiskData] = useState(null);
  const [dismissed, setDismissed] = useState(false);
  const slideAnim = useRef(new Animated.Value(-100)).current;

  useEffect(() => {
    setDismissed(false);
    loadRiskScore();
  }, [mealAccountId]);

  const loadRiskScore = async () => {
    try {
      const res = await paymentsAPI.riskScore(mealAccountId);
      setRiskData(res.data);
      if (res.data.at_risk) {
        slideAnim.setValue(-100);
        Animated.spring(slideAnim, {
          toValue: 0, tension: 50, friction: 8, useNativeDriver: true,
        }).start();
      }
    } catch (e) {
      console.log('Risk score error:', e.message);
    }
  };

  const handleDismiss = () => {
    Animated.timing(slideAnim, {
      toValue: -100, duration: 200, useNativeDriver: true,
    }).start(() => setDismissed(true));
  };

  if (!riskData || !riskData.at_risk || dismissed) {
    return null;
  }

  const prob = riskData.risk_probability;
  const days = riskData.estimated_days_remaining;
  const isHighRisk = prob >= 0.80;

  return (
    <Animated.View style={[
      styles.banner,
      { transform: [{ translateY: slideAnim }] },
      isHighRisk ? styles.bannerHigh : styles.bannerMedium
    ]}>
      <View style={styles.bannerContent}>
        <Feather
          name={isHighRisk ? 'alert-octagon' : 'alert-triangle'}
          size={26}
          color={isHighRisk ? '#C0392B' : '#D07020'}
          style={styles.bannerIcon}
        />
        <View style={styles.bannerText}>
          <Text style={styles.bannerTitle}>
            {isHighRisk ? 'Balance Running Out Soon' : 'Low Balance Predicted'}
          </Text>
          <Text style={styles.bannerSub}>
            {riskData.student_name}'s balance estimated to last ~
            {days < 1 ? 'less than 1' : Math.round(days)} more day
            {days !== 1 ? 's' : ''}. KES {riskData.balance_ksh?.toLocaleString(
              'en-KE', { minimumFractionDigits: 2 })} remaining.
          </Text>
          <View style={styles.bannerModelRow}>
            <MaterialCommunityIcons name="robot-outline" size={11} color="#9CA3AF" />
            <Text style={styles.bannerModel}>
              Predicted by Random Forest Classifier ({(prob * 100).toFixed(0)}% confidence)
            </Text>
          </View>
        </View>
      </View>

      <View style={styles.bannerActions}>
        <TouchableOpacity
          style={styles.topUpNowBtn}
          onPress={() => navigation.navigate('TopUp')}
        >
          <Text style={styles.topUpNowText}>Top Up Now</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.dismissBtn} onPress={handleDismiss}>
          <Text style={styles.dismissText}>Dismiss</Text>
        </TouchableOpacity>
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  banner: {
    marginHorizontal: 20, marginTop: 12, borderRadius: 16, padding: 16,
    shadowColor: '#000', shadowOpacity: 0.1, shadowRadius: 8, elevation: 4,
  },
  bannerHigh: { backgroundColor: '#FEE2E2' },
  bannerMedium: { backgroundColor: '#FEF3C7' },
  bannerContent: { flexDirection: 'row', gap: 12, marginBottom: 12 },
  bannerIcon: { marginTop: 2 },
  bannerText: { flex: 1 },
  bannerTitle: {
    fontSize: 14, fontWeight: '700', color: '#1A3A5C', marginBottom: 4,
  },
  bannerSub: {
    fontSize: 12, color: '#374151', lineHeight: 18, marginBottom: 6,
  },
  bannerModelRow: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  bannerModel: { fontSize: 10, color: '#9CA3AF', fontStyle: 'italic' },
  bannerActions: { flexDirection: 'row', gap: 10 },
  topUpNowBtn: {
    flex: 1, backgroundColor: '#1A6E3C', borderRadius: 8,
    paddingVertical: 10, alignItems: 'center',
  },
  topUpNowText: { color: '#fff', fontSize: 13, fontWeight: '700' },
  dismissBtn: {
    paddingVertical: 10, paddingHorizontal: 16,
    borderWidth: 1, borderColor: '#D1D5DB', borderRadius: 8,
    alignItems: 'center', backgroundColor: '#fff',
  },
  dismissText: { color: '#6B7280', fontSize: 13, fontWeight: '600' },
});
