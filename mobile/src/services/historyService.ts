import AsyncStorage from '@react-native-async-storage/async-storage';
import type { AlertResponse } from '../types/alert';

const HISTORY_KEY = '@orbital_trust/history';

export async function saveToHistory(alert: AlertResponse): Promise<void> {
  const raw = await AsyncStorage.getItem(HISTORY_KEY);
  const existing: AlertResponse[] = raw ? JSON.parse(raw) : [];
  const filtered = existing.filter((a) => a.event_id !== alert.event_id);
  await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify([alert, ...filtered]));
}

export async function getHistory(): Promise<AlertResponse[]> {
  const raw = await AsyncStorage.getItem(HISTORY_KEY);
  if (!raw) return [];
  const items: AlertResponse[] = JSON.parse(raw);
  return items.sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
  );
}
