import AsyncStorage from '@react-native-async-storage/async-storage';
import { generatedAlerts } from './generatedMockData';

import type {
  AlertResponse,
  ContractSource,
  DetectedClass,
  ImageQuality,
  RiskLevel,
} from '../types/alert';

declare const __DEV__: boolean | undefined;
declare const process: {
  env?: Record<string, string | undefined>;
};

const HISTORY_KEY = '@orbital_trust/history';
const RISK_LEVELS = new Set<RiskLevel>(['baixo', 'medio', 'alto']);
const DETECTED_CLASSES = new Set<DetectedClass>([
  'vegetacao',
  'solo_exposto',
  'agua',
  'queimada',
  'baixa_visibilidade',
]);
const IMAGE_QUALITIES = new Set<ImageQuality>(['boa', 'media', 'baixa']);
const CONTRACT_SOURCES = new Set<ContractSource>([
  'Sentinel-2',
  'Landsat',
  'FIRMS',
  'INPE',
]);

export async function clearHistory(): Promise<void> {
  await AsyncStorage.removeItem(HISTORY_KEY);
}

export async function saveToHistory(alert: AlertResponse): Promise<void> {
  const raw = await AsyncStorage.getItem(HISTORY_KEY);
  const existing = parseHistory(raw);
  const safeAlert = sanitizeAlertForHistory(alert);
  const filtered = existing.filter((a) => a.event_id !== safeAlert.event_id);
  await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify([safeAlert, ...filtered]));
}

export async function getHistory(): Promise<AlertResponse[]> {
  const raw = await AsyncStorage.getItem(HISTORY_KEY);
  const items = parseHistory(raw);

  if (items.length === 0) {
    return [...generatedAlerts].sort(
      (a, b) => getTimestampMs(b.timestamp) - getTimestampMs(a.timestamp),
    );
  }

  return [...items].sort(
    (a, b) => getTimestampMs(b.timestamp) - getTimestampMs(a.timestamp),
  );
}

export function parseHistory(raw: string | null): AlertResponse[] {
  if (!raw) return [];

  try {
    const parsed: unknown = JSON.parse(raw);

    if (!Array.isArray(parsed)) {
      logStorageWarning('Historico local ignorado: formato raiz invalido.');
      return [];
    }

    const history = parsed
      .filter((item) => isAlertResponse(item))
      .map((item) => sanitizeAlertForHistory(item));

    if (history.length !== parsed.length) {
      logStorageWarning('Historico local contem itens incompletos ou invalidos.');
    }

    return history;
  } catch (error) {
    logStorageWarning(
      `Historico local ignorado: JSON invalido (${formatError(error)}).`,
    );
    return [];
  }
}

function sanitizeAlertForHistory(alert: AlertResponse): AlertResponse {
  const safeAlert: AlertResponse = {
    event_id: alert.event_id,
    timestamp: alert.timestamp,
    detected_class: alert.detected_class,
    risk_level: alert.risk_level,
    analysis_confidence: alert.analysis_confidence,
    explanation: alert.explanation,
    recommendation: alert.recommendation,
    model_version: alert.model_version,
  };

  if (isPercentage0To100(alert.class_percentage)) {
    safeAlert.class_percentage = alert.class_percentage;
  }
  if (isRatio0To1(alert.change_score)) safeAlert.change_score = alert.change_score;
  if (isRatio0To1(alert.cloud_score)) safeAlert.cloud_score = alert.cloud_score;
  if (isRatio0To1(alert.shadow_score)) safeAlert.shadow_score = alert.shadow_score;
  if (isFiniteNumber(alert.brightness_score)) {
    safeAlert.brightness_score = alert.brightness_score;
  }
  if (isFiniteNumber(alert.blur_score)) safeAlert.blur_score = alert.blur_score;
  if (isImageQuality(alert.image_quality)) safeAlert.image_quality = alert.image_quality;
  if (isRatio0To1(alert.cv_confidence)) safeAlert.cv_confidence = alert.cv_confidence;
  if (typeof alert.algorithm_version === 'string') {
    safeAlert.algorithm_version = alert.algorithm_version;
  }
  if (typeof alert.source === 'string') safeAlert.source = alert.source;
  if (isContractSource(alert.contract_source)) {
    safeAlert.contract_source = alert.contract_source;
  }
  if (typeof alert.visual_product === 'string') {
    safeAlert.visual_product = alert.visual_product;
  }
  if (typeof alert.tile_provider === 'string') safeAlert.tile_provider = alert.tile_provider;
  if (typeof alert.image_url === 'string') safeAlert.image_url = alert.image_url;

  return safeAlert;
}

function isAlertResponse(value: unknown): value is AlertResponse {
  if (!isRecord(value)) return false;

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
      isPercentage0To100(value.class_percentage)) &&
    (value.change_score === undefined || isRatio0To1(value.change_score)) &&
    (value.cloud_score === undefined || isRatio0To1(value.cloud_score)) &&
    (value.shadow_score === undefined || isRatio0To1(value.shadow_score)) &&
    (value.brightness_score === undefined || isFiniteNumber(value.brightness_score)) &&
    (value.blur_score === undefined || isFiniteNumber(value.blur_score)) &&
    (value.image_quality === undefined || isImageQuality(value.image_quality)) &&
    (value.cv_confidence === undefined || isRatio0To1(value.cv_confidence)) &&
    (value.contract_source === undefined || isContractSource(value.contract_source))
  );
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

function isRatio0To1(value: unknown): value is number {
  return isFiniteNumber(value) && value >= 0 && value <= 1;
}

function isImageQuality(value: unknown): value is ImageQuality {
  return typeof value === 'string' && IMAGE_QUALITIES.has(value as ImageQuality);
}

function isContractSource(value: unknown): value is ContractSource {
  return typeof value === 'string' && CONTRACT_SOURCES.has(value as ContractSource);
}

function getTimestampMs(timestamp: string): number {
  const parsed = new Date(timestamp).getTime();
  return Number.isFinite(parsed) ? parsed : 0;
}

function logStorageWarning(message: string): void {
  if (isDevelopment()) {
    console.warn(`[historyService] ${message}`);
  }
}

function isDevelopment(): boolean {
  if (typeof __DEV__ !== 'undefined') return __DEV__;
  if (typeof process !== 'undefined') return process.env?.NODE_ENV !== 'production';
  return false;
}

function formatError(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}