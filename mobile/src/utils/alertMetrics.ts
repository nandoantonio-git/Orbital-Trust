import type { AlertResponse, ImageQuality } from '../types/alert';

export const LOW_QUALITY_CAUTION =
  'A imagem possui limitações visuais. Use este alerta como apoio e valide com outras fontes antes de uma decisão crítica.';

const IMAGE_QUALITY_LABELS: Record<ImageQuality, string> = {
  boa: 'boa',
  media: 'média',
  baixa: 'baixa',
};

export function formatImageQuality(quality: ImageQuality | undefined): string {
  return quality === undefined ? 'Não disponível' : IMAGE_QUALITY_LABELS[quality];
}

export function formatMetricPercent(value: number | undefined): string {
  if (value === undefined || !Number.isFinite(value)) {
    return 'Não disponível';
  }

  const percentage = value <= 1 ? value * 100 : value;
  return `${Math.round(percentage)}%`;
}

export function formatVisualEvidenceSummary(alert: AlertResponse): string {
  const quality = alert.image_quality;
  const confidence = alert.cv_confidence;

  if (quality !== undefined && confidence !== undefined) {
    return `Evidência visual: qualidade ${formatImageQuality(quality)} • CV ${formatMetricPercent(confidence)}`;
  }

  if (quality !== undefined) {
    return `Evidência visual: qualidade ${formatImageQuality(quality)}`;
  }

  if (confidence !== undefined) {
    return `Evidência visual: CV ${formatMetricPercent(confidence)}`;
  }

  return 'Evidência visual: não disponível';
}
