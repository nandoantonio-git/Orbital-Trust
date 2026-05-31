import type { AlertResponse, DetectedClass, RiskLevel } from '../types/alert';
import { generatedAlerts } from './generatedMockData';

declare const process: {
  env?: Record<string, string | undefined>;
};

type AlertServiceMode = 'mock' | 'api';

const DEFAULT_MODE: AlertServiceMode = 'mock';
const BASE_URL =
  readExpoEnv('EXPO_PUBLIC_ALERTS_BASE_URL') ?? 'https://api.orbitaltrust.io/v1';
const ALERT_SERVICE_MODE = parseMode(
  readExpoEnv('EXPO_PUBLIC_ALERTS_API_MODE') ?? DEFAULT_MODE,
);

const RISK_LEVELS = new Set<RiskLevel>(['baixo', 'medio', 'alto']);
const DETECTED_CLASSES = new Set<DetectedClass>([
  'vegetacao',
  'solo_exposto',
  'agua',
  'queimada',
  'baixa_visibilidade',
]);
const MOCK_ALERTS = validateMockAlerts(generatedAlerts);

export async function getAlerts(): Promise<AlertResponse[]> {
  if (ALERT_SERVICE_MODE !== 'api') {
    return MOCK_ALERTS;
  }

  const data = await fetchJson(`${BASE_URL}/alerts`);

  if (!Array.isArray(data) || !data.every(isAlertResponse)) {
    throw new Error('Resposta invalida da API: esperado AlertResponse[].');
  }

  return data;
}

export async function getAlertById(id: string): Promise<AlertResponse | null> {
  if (ALERT_SERVICE_MODE !== 'api') {
    return MOCK_ALERTS.find((a) => a.event_id === id) ?? null;
  }

  const data = await fetchJson(`${BASE_URL}/alerts/${encodeURIComponent(id)}`, {
    returnNullOnNotFound: true,
  });

  if (data === null) {
    return null;
  }

  if (!isAlertResponse(data)) {
    throw new Error('Resposta invalida da API: esperado AlertResponse.');
  }

  return data;
}

function readExpoEnv(name: string): string | undefined {
  if (typeof process === 'undefined') {
    return undefined;
  }

  return process.env?.[name];
}

function parseMode(value: string): AlertServiceMode {
  return value === 'api' ? 'api' : 'mock';
}

async function fetchJson(
  url: string,
  options: { returnNullOnNotFound?: boolean } = {},
): Promise<unknown | null> {
  let response: Response;

  try {
    response = await fetch(url);
  } catch (error) {
    throw new Error(`Falha de rede ao acessar API de alertas: ${formatError(error)}`);
  }

  if (options.returnNullOnNotFound && response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(`API de alertas respondeu com status ${response.status}.`);
  }

  try {
    return await response.json();
  } catch (error) {
    throw new Error(`Resposta invalida da API de alertas: ${formatError(error)}`);
  }
}

function isAlertResponse(value: unknown): value is AlertResponse {
  if (!isRecord(value)) {
    return false;
  }

  return (
    typeof value.event_id === 'string' &&
    typeof value.timestamp === 'string' &&
    typeof value.detected_class === 'string' &&
    DETECTED_CLASSES.has(value.detected_class as DetectedClass) &&
    typeof value.risk_level === 'string' &&
    RISK_LEVELS.has(value.risk_level as RiskLevel) &&
    isFiniteNumber(value.analysis_confidence) &&
    typeof value.explanation === 'string' &&
    typeof value.recommendation === 'string' &&
    typeof value.model_version === 'string' &&
    (value.class_percentage === undefined ||
      isPercentage0To100(value.class_percentage))
  );
}

function validateMockAlerts(alerts: AlertResponse[]): AlertResponse[] {
  const invalid = alerts.find(
    (alert) => !isAlertResponse(alert) || !isPercentage0To100(alert.class_percentage),
  );

  if (invalid) {
    throw new Error(
      `Mock invalido: class_percentage deve usar percentual 0-100 (${invalid.event_id}).`,
    );
  }

  return alerts;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function isPercentage0To100(value: unknown): value is number {
  return isFiniteNumber(value) && value >= 0 && value <= 100;
}

function formatError(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
