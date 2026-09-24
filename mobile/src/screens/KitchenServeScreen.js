import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, FlatList,
  StyleSheet, ActivityIndicator, Alert, Modal
} from 'react-native';
import { Feather } from '@expo/vector-icons';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { useAuth } from '../context/AuthContext';
import { mealsAPI } from '../services/api';

export default function KitchenServeScreen() {
  const { user, logout } = useAuth();
  const [query, setQuery] = useState('');
  const [students, setStudents] = useState([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);

  const [menuItems, setMenuItems] = useState([]);
  const [combos, setCombos] = useState([]);
  const [servingStudent, setServingStudent] = useState(null);
  const [selectedItems, setSelectedItems] = useState([]);
  const [itemSearch, setItemSearch] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const [showScanner, setShowScanner] = useState(false);
  const [cameraPermission, requestCameraPermission] = useCameraPermissions();
  // onBarcodeScanned keeps firing for every frame the code is visible in —
  // this guards against handling the same scan (and firing the lookup
  // request) many times over before the modal has a chance to close.
  const scanHandledRef = useRef(false);

  useEffect(() => {
    mealsAPI.menuList().then(res => setMenuItems(res.data)).catch(() => {});
    mealsAPI.comboList().then(res => setCombos(res.data)).catch(() => {});
  }, []);

  const runSearch = useCallback(async (q) => {
    if (!q || q.trim().length < 2) {
      setStudents([]);
      setSearched(false);
      return;
    }
    setLoading(true);
    try {
      const res = await mealsAPI.lookup(q.trim());
      setStudents(res.data.students);
      setSearched(true);
    } catch (e) {
      Alert.alert('Search failed', e.response?.data?.error || 'Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  const openScanner = async () => {
    if (!cameraPermission?.granted) {
      const res = await requestCameraPermission();
      if (!res.granted) {
        Alert.alert(
          'Camera permission needed',
          'Allow camera access to scan student QR codes, or search by name instead.'
        );
        return;
      }
    }
    scanHandledRef.current = false;
    setShowScanner(true);
  };

  const handleBarcodeScanned = async ({ data }) => {
    if (scanHandledRef.current) return;
    scanHandledRef.current = true;
    setShowScanner(false);
    setQuery('');
    setLoading(true);
    try {
      const res = await mealsAPI.lookupByQR(data);
      setStudents(res.data.students);
      setSearched(true);
    } catch (e) {
      Alert.alert(
        'QR code not recognized',
        e.response?.data?.error || 'Try scanning again, or search by name.'
      );
      setStudents([]);
      setSearched(true);
    } finally {
      setLoading(false);
    }
  };

  const openServeModal = (student) => {
    setServingStudent(student);
    setSelectedItems([]);
    setItemSearch('');
  };

  const toggleItem = (itemId) => {
    setSelectedItems(prev =>
      prev.includes(itemId) ? prev.filter(id => id !== itemId) : [...prev, itemId]
    );
  };

  const addCombo = (combo) => {
    setSelectedItems(prev => {
      const comboItemIds = combo.items.map(i => i.id);
      const merged = new Set(prev);
      comboItemIds.forEach(id => merged.add(id));
      return Array.from(merged);
    });
  };

  const totalCents = selectedItems.reduce((sum, id) => {
    const item = menuItems.find(m => m.id === id);
    return sum + (item ? item.price_cents : 0);
  }, 0);

  const searchLower = itemSearch.trim().toLowerCase();
  const filteredItems = searchLower
    ? menuItems.filter(i => i.name.toLowerCase().includes(searchLower))
    : menuItems;
  const filteredCombos = searchLower
    ? combos.filter(c => c.name.toLowerCase().includes(searchLower))
    : combos;

  const handleConfirmServe = async () => {
    if (!servingStudent || selectedItems.length === 0) return;
    setSubmitting(true);
    try {
      const res = await mealsAPI.serve(servingStudent.id, selectedItems);
      setServingStudent(null);
      setSelectedItems([]);
      Alert.alert(
        'Meal recorded',
        `${res.data.student} — ${res.data.items.join(', ')}\n` +
        `KES ${res.data.deducted_ksh.toFixed(2)} deducted, new balance KES ${res.data.new_balance_ksh.toFixed(2)}\n` +
        `Served by ${res.data.served_by}`
      );
      runSearch(query);
    } catch (e) {
      Alert.alert('Could not record meal', e.response?.data?.error || 'Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleLogout = () => {
    Alert.alert('Log out', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Log out', style: 'destructive', onPress: logout }
    ]);
  };

  const renderItem = ({ item }) => {
    const disabled = !item.eligible;
    return (
      <View style={styles.card}>
        <View style={styles.cardInfo}>
          <Text style={styles.studentName}>{item.full_name}</Text>
          <Text style={styles.studentBalance}>
            KES {item.balance_ksh.toFixed(2)}
            {item.credit_limit_ksh > 0 && (
              <Text style={styles.creditNote}> (+KES {item.credit_limit_ksh.toFixed(2)} credit)</Text>
            )}
          </Text>
          {item.already_served_today && (
            <View style={styles.badgeRow}>
              <Feather name="check-circle" size={12} color="#1A6E3C" />
              <Text style={styles.badgeServed}>Already served today</Text>
            </View>
          )}
        </View>
        <TouchableOpacity
          style={[styles.serveBtn, disabled && styles.serveBtnDisabled]}
          onPress={() => openServeModal(item)}
          disabled={disabled}
        >
          <Text style={styles.serveBtnText}>
            {item.already_served_today ? 'Served' : 'Serve'}
          </Text>
        </TouchableOpacity>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>Kitchen · {user?.school?.name}</Text>
          <Text style={styles.name}>{user?.full_name}</Text>
        </View>
        <TouchableOpacity onPress={handleLogout}>
          <Text style={styles.logout}>Log out</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.searchWrap}>
        <View style={styles.searchRow}>
          <TextInput
            style={styles.searchInput}
            placeholder="Search student by name..."
            placeholderTextColor="#9CA3AF"
            value={query}
            onChangeText={(v) => { setQuery(v); runSearch(v); }}
            autoCapitalize="words"
          />
          <TouchableOpacity style={styles.scanBtn} onPress={openScanner}>
            <Feather name="camera" size={18} color="#fff" />
          </TouchableOpacity>
        </View>
        <Text style={styles.scanHint}>Lost QR card? Search by name instead.</Text>
      </View>

      {loading ? (
        <ActivityIndicator size="large" color="#1A6E3C" style={{ marginTop: 40 }} />
      ) : (
        <FlatList
          data={students}
          keyExtractor={(item) => String(item.id)}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Text style={styles.emptyText}>
                {searched ? 'No students found' : 'Type a name to search'}
              </Text>
              <Text style={styles.emptySub}>
                {searched
                  ? 'Try a different spelling'
                  : 'e.g. "John" or "Wanjiku"'}
              </Text>
            </View>
          }
        />
      )}

      <Modal
        visible={!!servingStudent}
        transparent
        animationType="slide"
        onRequestClose={() => setServingStudent(null)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modal}>
            <Text style={styles.modalTitle}>Serve {servingStudent?.full_name}</Text>
            <Text style={styles.modalSub}>Search a meal or a meal combination, or pick items below</Text>

            <TextInput
              style={styles.itemSearchInput}
              placeholder="Search food or combination..."
              placeholderTextColor="#9CA3AF"
              value={itemSearch}
              onChangeText={setItemSearch}
            />

            {filteredCombos.length > 0 && (
              <View style={styles.comboSection}>
                <Text style={styles.comboSectionLabel}>MEAL COMBINATIONS</Text>
                {filteredCombos.map(combo => (
                  <TouchableOpacity
                    key={combo.id}
                    style={styles.comboBtn}
                    onPress={() => addCombo(combo)}
                  >
                    <Text style={styles.comboBtnName}>{combo.name}</Text>
                    <Text style={styles.comboBtnSub}>
                      {combo.items.map(i => i.name).join(', ')}
                    </Text>
                    <Text style={styles.comboBtnPrice}>
                      KES {combo.total_price_ksh.toFixed(2)}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            )}

            {menuItems.length === 0 ? (
              <Text style={styles.emptyText}>No menu items configured yet.</Text>
            ) : filteredItems.length === 0 ? (
              <Text style={styles.emptyText}>No matching items.</Text>
            ) : (
              <FlatList
                data={filteredItems}
                keyExtractor={item => String(item.id)}
                style={{ maxHeight: 220 }}
                renderItem={({ item }) => {
                  const checked = selectedItems.includes(item.id);
                  return (
                    <TouchableOpacity style={styles.itemRow} onPress={() => toggleItem(item.id)}>
                      <Feather
                        name={checked ? 'check-square' : 'square'}
                        size={18}
                        color={checked ? '#1A6E3C' : '#9CA3AF'}
                      />
                      <Text style={styles.itemName}>{item.name}</Text>
                      <Text style={styles.itemPrice}>KES {item.price_ksh.toFixed(2)}</Text>
                    </TouchableOpacity>
                  );
                }}
              />
            )}

            <View style={styles.totalRow}>
              <Text style={styles.totalLabel}>Total</Text>
              <Text style={styles.totalValue}>KES {(totalCents / 100).toFixed(2)}</Text>
            </View>

            <View style={styles.modalActions}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setServingStudent(null)}>
                <Text style={styles.cancelBtnText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.confirmBtn, (selectedItems.length === 0 || submitting) && styles.serveBtnDisabled]}
                onPress={handleConfirmServe}
                disabled={selectedItems.length === 0 || submitting}
              >
                {submitting
                  ? <ActivityIndicator color="#fff" size="small" />
                  : <Text style={styles.confirmBtnText}>Confirm & Record</Text>
                }
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      <Modal
        visible={showScanner}
        animationType="slide"
        onRequestClose={() => setShowScanner(false)}
      >
        <View style={styles.scannerContainer}>
          <CameraView
            style={StyleSheet.absoluteFillObject}
            facing="back"
            barcodeScannerSettings={{ barcodeTypes: ['qr'] }}
            onBarcodeScanned={handleBarcodeScanned}
          />
          <View style={styles.scannerOverlay}>
            <View style={styles.scannerHeader}>
              <Text style={styles.scannerTitle}>Scan Student QR Code</Text>
              <TouchableOpacity onPress={() => setShowScanner(false)} style={styles.scannerCloseBtn}>
                <Feather name="x" size={22} color="#fff" />
              </TouchableOpacity>
            </View>
            <View style={styles.scanBox} />
            <Text style={styles.scannerHint}>
              Point the camera at the student's ID card or wristband
            </Text>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F7F9FC' },
  header: { backgroundColor: '#1A3A5C', padding: 20, paddingTop: 56,
            flexDirection: 'row', justifyContent: 'space-between',
            alignItems: 'flex-start' },
  greeting: { color: '#A8D8C0', fontSize: 12 },
  name: { color: '#fff', fontSize: 18, fontWeight: '700', marginTop: 2 },
  logout: { color: '#F87171', fontSize: 13, marginTop: 4 },
  searchWrap: { padding: 16 },
  searchRow: { flexDirection: 'row', gap: 10, alignItems: 'center' },
  searchInput: { flex: 1, backgroundColor: '#fff', borderWidth: 1, borderColor: '#E5E7EB',
                 borderRadius: 10, paddingHorizontal: 16, paddingVertical: 12,
                 fontSize: 15, color: '#111827' },
  scanBtn: { backgroundColor: '#1A3A5C', borderRadius: 10,
             width: 46, height: 46, alignItems: 'center', justifyContent: 'center' },
  scanHint: { fontSize: 11, color: '#9CA3AF', marginTop: 8 },
  list: { paddingHorizontal: 16, paddingBottom: 24 },
  card: { backgroundColor: '#fff', borderRadius: 12, padding: 16,
          marginBottom: 10, flexDirection: 'row', justifyContent: 'space-between',
          alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.04,
          shadowRadius: 6, elevation: 2 },
  cardInfo: { flex: 1 },
  studentName: { fontSize: 15, fontWeight: '700', color: '#1A3A5C' },
  studentBalance: { fontSize: 13, color: '#6B7280', marginTop: 2 },
  creditNote: { fontSize: 11, color: '#6B9AB8' },
  badgeRow: { flexDirection: 'row', alignItems: 'center', gap: 5, marginTop: 4 },
  badgeServed: { fontSize: 12, color: '#1A6E3C', fontWeight: '600' },
  serveBtn: { backgroundColor: '#1A6E3C', borderRadius: 8,
              paddingVertical: 10, paddingHorizontal: 18 },
  serveBtnDisabled: { backgroundColor: '#CBD5E1' },
  serveBtnText: { color: '#fff', fontSize: 13, fontWeight: '700' },
  empty: { alignItems: 'center', paddingTop: 60 },
  emptyText: { fontSize: 16, fontWeight: '700', color: '#1A3A5C' },
  emptySub: { fontSize: 13, color: '#9CA3AF', marginTop: 6 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.4)', justifyContent: 'flex-end' },
  modal: { backgroundColor: '#fff', borderTopLeftRadius: 20, borderTopRightRadius: 20,
           padding: 24, maxHeight: '80%' },
  modalTitle: { fontSize: 18, fontWeight: '700', color: '#1A3A5C' },
  modalSub: { fontSize: 13, color: '#6B7280', marginTop: 4, marginBottom: 12 },
  itemSearchInput: { backgroundColor: '#F7F9FC', borderWidth: 1, borderColor: '#E5E7EB',
                     borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10,
                     fontSize: 13, color: '#111827', marginBottom: 12 },
  comboSection: { marginBottom: 12 },
  comboSectionLabel: { fontSize: 10, fontWeight: '700', color: '#6B9AB8',
                       letterSpacing: 0.4, marginBottom: 6 },
  comboBtn: { backgroundColor: '#EEF0FB', borderWidth: 1, borderColor: '#C7CDF0',
              borderRadius: 8, padding: 10, marginBottom: 6 },
  comboBtnName: { fontSize: 13, fontWeight: '700', color: '#3A4AB0' },
  comboBtnSub: { fontSize: 11, color: '#6B7280', marginTop: 2 },
  comboBtnPrice: { fontSize: 12, fontWeight: '700', color: '#1A3A5C', marginTop: 4 },
  itemRow: { flexDirection: 'row', alignItems: 'center', gap: 10,
             paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#F3F4F6' },
  itemName: { flex: 1, fontSize: 14, color: '#374151' },
  itemPrice: { fontSize: 13, fontWeight: '600', color: '#1A3A5C' },
  totalRow: { flexDirection: 'row', justifyContent: 'space-between',
              paddingVertical: 16 },
  totalLabel: { fontSize: 15, color: '#1A3A5C' },
  totalValue: { fontSize: 15, fontWeight: '700', color: '#1A3A5C' },
  modalActions: { flexDirection: 'row', gap: 10, paddingBottom: 12 },
  cancelBtn: { flex: 1, backgroundColor: '#F3F4F6', borderRadius: 10,
               paddingVertical: 14, alignItems: 'center' },
  cancelBtnText: { color: '#374151', fontSize: 14, fontWeight: '600' },
  confirmBtn: { flex: 1, backgroundColor: '#1A6E3C', borderRadius: 10,
                paddingVertical: 14, alignItems: 'center' },
  confirmBtnText: { color: '#fff', fontSize: 14, fontWeight: '700' },
  scannerContainer: { flex: 1, backgroundColor: '#000' },
  scannerOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.15)',
                    justifyContent: 'space-between' },
  scannerHeader: { flexDirection: 'row', justifyContent: 'space-between',
                   alignItems: 'center', paddingTop: 56, paddingHorizontal: 20 },
  scannerTitle: { color: '#fff', fontSize: 16, fontWeight: '700' },
  scannerCloseBtn: { padding: 6 },
  scanBox: { alignSelf: 'center', width: 220, height: 220, borderRadius: 16,
             borderWidth: 3, borderColor: '#1A6E3C', backgroundColor: 'transparent' },
  scannerHint: { color: '#fff', fontSize: 13, textAlign: 'center',
                 paddingBottom: 48, paddingHorizontal: 32 },
});
