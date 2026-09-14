import React, { useEffect, useRef } from 'react';
import {
  View, Text, TouchableOpacity,
  StyleSheet, Animated
} from 'react-native';
import { Feather } from '@expo/vector-icons';

const AnimatedFeather = Animated.createAnimatedComponent(Feather);

export default function LowBalanceAlertScreen({ navigation, route }) {
  const { balance_ksh, student_name } = route.params || {};
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.08,
          duration: 700,
          useNativeDriver: true
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 700,
          useNativeDriver: true
        }),
      ])
    ).start();
  }, []);

  return (
    <View style={styles.container}>
      <AnimatedFeather
        name="alert-triangle"
        size={64}
        color="#D07020"
        style={[styles.icon, { transform: [{ scale: pulseAnim }] }]}
      />

      <Text style={styles.title}>Low Meal Balance</Text>
      <Text style={styles.name}>{student_name}</Text>

      <View style={styles.balanceCard}>
        <Text style={styles.balanceLabel}>Current balance</Text>
        <Text style={styles.balanceAmount}>
          KES {balance_ksh?.toFixed(2) || '0.00'}
        </Text>
        <Text style={styles.balanceMin}>
          Minimum required: KES 50.00
        </Text>
      </View>

      <Text style={styles.message}>
        This student may not be able to collect their next
        meal without a top-up. Top up now to avoid
        service disruption.
      </Text>

      <TouchableOpacity
        style={styles.topUpBtn}
        onPress={() => navigation.navigate('TopUp')}
      >
        <Feather name="credit-card" size={16} color="#fff" />
        <Text style={styles.topUpBtnText}>Top Up Now</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.dismissBtn}
        onPress={() => navigation.navigate('Home')}
      >
        <Text style={styles.dismissText}>Dismiss</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#FFF7ED',
               justifyContent: 'center', alignItems: 'center',
               padding: 32 },
  icon: { marginBottom: 16 },
  title: { fontSize: 26, fontWeight: '700',
           color: '#92400E', textAlign: 'center' },
  name: { fontSize: 16, color: '#6B7280',
          marginTop: 4, marginBottom: 24 },
  balanceCard: { backgroundColor: '#fff', borderRadius: 16,
                 padding: 24, width: '100%', marginBottom: 20,
                 alignItems: 'center',
                 shadowColor: '#000', shadowOpacity: 0.06,
                 shadowRadius: 10, elevation: 3,
                 borderWidth: 1, borderColor: '#FDE68A' },
  balanceLabel: { fontSize: 13, color: '#6B7280', marginBottom: 4 },
  balanceAmount: { fontSize: 36, fontWeight: '700', color: '#C0392B' },
  balanceMin: { fontSize: 12, color: '#9CA3AF', marginTop: 6 },
  message: { fontSize: 14, color: '#6B7280', textAlign: 'center',
             lineHeight: 21, marginBottom: 32 },
  topUpBtn: { backgroundColor: '#D07020', borderRadius: 12,
              paddingVertical: 16, paddingHorizontal: 48,
              marginBottom: 12, flexDirection: 'row',
              alignItems: 'center', justifyContent: 'center', gap: 8 },
  topUpBtnText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  dismissBtn: { padding: 12 },
  dismissText: { color: '#9CA3AF', fontSize: 14 },
});
