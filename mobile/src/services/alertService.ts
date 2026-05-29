import { AlertResponse } from '../types/alert';
import { mockAlerts } from './mockData';

const BASE_URL = 'https://api.orbitaltrust.io/v1';

export async function getAlerts(): Promise<AlertResponse[]> {
  return mockAlerts;
}

export async function getAlertById(id: string): Promise<AlertResponse | null> {
  return mockAlerts.find((a) => a.event_id === id) ?? null;
}
