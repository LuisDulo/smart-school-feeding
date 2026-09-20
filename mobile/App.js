// Must be the very first import — registers the native gesture-handler
// module before anything else touches it (react-native-gesture-handler's
// own setup requirement; @react-navigation/stack depends on it).
import 'react-native-gesture-handler';
import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { ActivityIndicator, View } from 'react-native';
import { AuthProvider, useAuth } from './src/context/AuthContext';
import LoginScreen from './src/screens/LoginScreen';
import RegisterScreen from './src/screens/RegisterScreen';
import HomeScreen from './src/screens/HomeScreen';
import TopUpScreen from './src/screens/TopUpScreen';
import PaymentStatusScreen from './src/screens/PaymentStatusScreen';
import PaymentHistoryScreen from './src/screens/PaymentHistoryScreen';
import LowBalanceAlertScreen from './src/screens/LowBalanceAlertScreen';
import KitchenServeScreen from './src/screens/KitchenServeScreen';
import RaiseIssueScreen from './src/screens/RaiseIssueScreen';
import MealConsumptionScreen from './src/screens/MealConsumptionScreen';
import ApplyCreditScreen from './src/screens/ApplyCreditScreen';
import PaymentReceiptScreen from './src/screens/PaymentReceiptScreen';
import BalanceTrendScreen from './src/screens/BalanceTrendScreen';
import MonthlyReportScreen from './src/screens/MonthlyReportScreen';
import ReminderSettingsScreen from './src/screens/ReminderSettingsScreen';
import QRCodeScreen from './src/screens/QRCodeScreen';

const Stack = createStackNavigator();

function AppNavigator() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
        <ActivityIndicator size="large" color="#1A6E3C" />
      </View>
    );
  }

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      {user?.role === 'kitchen' ? (
        // Kitchen staff only serve meals — none of the payment/balance
        // screens below are relevant to them.
        <Stack.Screen name="KitchenServe" component={KitchenServeScreen} />
      ) : user ? (
        <>
          <Stack.Screen name="Home" component={HomeScreen} />
          <Stack.Screen name="TopUp" component={TopUpScreen} />
          <Stack.Screen name="PaymentStatus" component={PaymentStatusScreen} />
          <Stack.Screen name="PaymentHistory" component={PaymentHistoryScreen} />
          <Stack.Screen name="LowBalanceAlert" component={LowBalanceAlertScreen} />
          <Stack.Screen name="MealConsumption" component={MealConsumptionScreen} />
          <Stack.Screen name="RaiseIssue" component={RaiseIssueScreen} />
          <Stack.Screen name="ApplyCredit" component={ApplyCreditScreen} />
          <Stack.Screen name="PaymentReceipt" component={PaymentReceiptScreen} />
          <Stack.Screen name="BalanceTrend" component={BalanceTrendScreen} />
          <Stack.Screen name="MonthlyReport" component={MonthlyReportScreen} />
          <Stack.Screen name="ReminderSettings" component={ReminderSettingsScreen} />
          <Stack.Screen name="QRCode" component={QRCodeScreen} />
        </>
      ) : (
        <>
          <Stack.Screen name="Login" component={LoginScreen} />
          <Stack.Screen name="Register" component={RegisterScreen} />
        </>
      )}
    </Stack.Navigator>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <NavigationContainer>
        <AppNavigator />
      </NavigationContainer>
    </AuthProvider>
  );
}
