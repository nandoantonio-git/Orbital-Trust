export type RiskLevel = 'baixo' | 'medio' | 'alto';

export type DetectedClass =
  | 'vegetacao'
  | 'solo_exposto'
  | 'agua'
  | 'queimada'
  | 'baixa_visibilidade';

export interface IoTPayload {
  event_id: string;
  timestamp: string;
  area_id: string;
  source: string;
  detected_class: DetectedClass;
  class_percentage: number;
  change_score: number;
  cloud_score: number;
  shadow_score: number;
  image_quality: number;
  cv_confidence: number;
  frame_reference: string;
}

export interface AlertResponse {
  event_id: string;
  timestamp: string;
  detected_class: DetectedClass;
  risk_level: RiskLevel;
  analysis_confidence: number;
  explanation: string;
  recommendation: string;
  model_version: string;
  class_percentage?: number;
  change_score?: number;
  source?: string;
  image_url?: string;
}
