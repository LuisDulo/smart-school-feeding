import { Platform } from 'react-native';
import Constants from 'expo-constants';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { authAPI } from './api';

// expo-notifications is loaded lazily, and never inside Expo Go: since SDK 53
// Expo Go on Android has no remote push support and the module throws as soon
// as it is imported there. Phone notifications need the development build
// (see mobile/README or the section on push notifications in the main README).
function getNotifications() {
  if (Constants.executionEnvironment === 'storeClient') return null; // Expo Go
  try {
    // eslint-disable-next-line global-require
    return require('expo-notifications');
  } catch (e) {
    console.log('expo-notifications unavailable:', e.message);
    return null;
  }
}

const PUSH_TOKEN_KEY = 'push_token';
const REMINDER_ID_KEY = 'reminder_notification_id';

// Where tapping a notification should take the user.
const SCREEN_FOR_TYPE = {
  meal: 'MealConsumption',
  topup: 'PaymentHistory',
  reminder: 'TopUp',
};

export function screenForNotificationData(data) {
  return SCREEN_FOR_TYPE[data?.type] || null;
}

/** Call once at startup: show alerts even while the app is open. */
export function configureNotifications() {
  const N = getNotifications();
  if (!N) return;
  N.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowBanner: true,
      shouldShowList: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
    }),
  });
}

async function ensurePermission(N) {
  if (Platform.OS === 'android') {
    // Android 13+ only shows the permission prompt once a channel exists.
    await N.setNotificationChannelAsync('default', {
      name: 'Meal & payment alerts',
      importance: N.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#1A6E3C',
    });
  }
  let { status } = await N.getPermissionsAsync();
  if (status !== 'granted') {
    ({ status } = await N.requestPermissionsAsync());
  }
  return status === 'granted';
}

/**
 * Ask for permission, get this phone's Expo push token and register it with
 * the backend so it can send meal / top-up / reminder alerts. Safe to call on
 * every login: it never throws and returns null when push isn't available.
 */
export async function registerForPush() {
  const N = getNotifications();
  if (!N) return null;
  try {
    if (!(await ensurePermission(N))) return null;
    const projectId =
      Constants?.expoConfig?.extra?.eas?.projectId ?? Constants?.easConfig?.projectId;
    if (!projectId) {
      console.log('Push: no EAS projectId — run "eas init" and rebuild the app.');
      return null;
    }
    const { data: token } = await N.getExpoPushTokenAsync({ projectId });
    await authAPI.registerPushToken(token, Platform.OS);
    await AsyncStorage.setItem(PUSH_TOKEN_KEY, token);
    return token;
  } catch (e) {
    console.log('Push registration error:', e.message);
    return null;
  }
}

/** Stop alerts for this account on this phone. Call BEFORE the session is cleared. */
export async function unregisterPush() {
  try {
    const token = await AsyncStorage.getItem(PUSH_TOKEN_KEY);
    if (token) await authAPI.removePushToken(token);
  } catch (e) {
    console.log('Push unregister error:', e.message);
  } finally {
    await AsyncStorage.removeItem(PUSH_TOKEN_KEY);
  }
}

/**
 * Keep the weekly "top up" phone reminder in step with Reminder Settings.
 * `day` is JS getDay() (0 = Sunday); Expo's weekly trigger counts 1 = Sunday.
 * Returns { scheduled, reason? } so the screen can tell the user what happened.
 */
export async function syncWeeklyReminder({ enabled, day, hour }) {
  const N = getNotifications();
  if (!N) return { scheduled: false, reason: 'unsupported' };
  try {
    const previous = await AsyncStorage.getItem(REMINDER_ID_KEY);
    if (previous) {
      await N.cancelScheduledNotificationAsync(previous);
      await AsyncStorage.removeItem(REMINDER_ID_KEY);
    }
    if (!enabled) return { scheduled: false };
    if (!(await ensurePermission(N))) return { scheduled: false, reason: 'denied' };
    const id = await N.scheduleNotificationAsync({
      content: {
        title: 'Top-up reminder',
        body: "Don't forget to top up your child's meal account this week.",
        data: { type: 'reminder' },
      },
      trigger: {
        type: N.SchedulableTriggerInputTypes.WEEKLY,
        weekday: day + 1,
        hour,
        minute: 0,
        channelId: 'default',
      },
    });
    await AsyncStorage.setItem(REMINDER_ID_KEY, id);
    return { scheduled: true };
  } catch (e) {
    console.log('Weekly reminder error:', e.message);
    return { scheduled: false, reason: 'error' };
  }
}

/**
 * Wire up "user tapped a notification" -> navigate. Returns an unsubscribe
 * function. `navigate(screenName)` is supplied by the navigation container.
 */
export function listenForNotificationTaps(navigate) {
  const N = getNotifications();
  if (!N) return () => {};
  const open = (response) => {
    const screen = screenForNotificationData(
      response?.notification?.request?.content?.data);
    if (screen) navigate(screen);
  };
  // App was closed and launched by tapping a notification.
  N.getLastNotificationResponseAsync?.().then(open).catch(() => {});
  const subscription = N.addNotificationResponseReceivedListener(open);
  return () => subscription.remove();
}
