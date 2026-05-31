export type RiskLevel = 'baixo' | 'medio' | 'alto';

export type DetectedClass =
  | 'vegetacao'
  | 'solo_exposto'
  | 'agua'
  | 'queimada'
  | 'baixa_visibilidade';

export type ContractSource = 'Sentinel-2' | 'Landsat' | 'FIRMS' | 'INPE';
export type ImageQuality = 'boa' | 'media' | 'baixa';

// Contract scale: percentage from 0 to 100, never a 0 to 1 ratio.
export type Percentage0To100 = number;

export interface IoTPayload {
  event_id: string;
  timestamp: string;
  area_id: string;
  source: ContractSource;
  detected_class: DetectedClass;
  class_percentage: Percentage0To100;
  change_score: number;
  cloud_score: number;
  shadow_score: number;
  brightness_score: number;
  blur_score: number;
  image_quality: ImageQuality;
  cv_confidence: number;
  frame_reference: string;
  algorithm_version: string;
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
  class_percentage?: Percentage0To100;
  change_score?: number;
  cloud_score?: number;
  shadow_score?: number;
  brightness_score?: number;
  blur_score?: number;
  image_quality?: ImageQuality;
  cv_confidence?: number;
  algorithm_version?: string;
  source?: string;
  contract_source?: ContractSource;
  visual_product?: string;
  tile_provider?: string;
  image_url?: string;
}
