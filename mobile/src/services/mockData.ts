import { AlertResponse } from '../types/alert';

export const mockAlerts: AlertResponse[] = [
  {
    event_id: 'EVT-2024-001',
    timestamp: '2024-11-15T14:32:00Z',
    detected_class: 'queimada',
    risk_level: 'alto',
    analysis_confidence: 0.94,
    explanation:
      'Queimada ativa detectada em 38% da área analisada. Frente de fogo em expansão com variação de 0.87 no change_score. Produto visual MODIS/GIBS com alta qualidade (0.92).',
    recommendation:
      'Acionar brigada de combate imediatamente. Notificar IBAMA e Defesa Civil. Interditar acesso à área.',
    model_version: 'orbital-ml-v1.2.0',
    class_percentage: 38.0,
    change_score: 0.87,
    source: 'MODIS/GIBS',
    visual_product: 'MODIS_Terra_CorrectedReflectance_TrueColor',
    tile_provider: 'NASA GIBS',
    image_url: 'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2024-10-01/250m/7/37/44.jpg',
  },
  {
    event_id: 'EVT-2024-002',
    timestamp: '2024-11-14T09:15:00Z',
    detected_class: 'solo_exposto',
    risk_level: 'alto',
    analysis_confidence: 0.91,
    explanation:
      'Solo exposto em 52% da área com erosão severa detectada. Change_score de 0.79 indica desmatamento recente. Produto visual MODIS/GIBS.',
    recommendation:
      'Solicitar vistoria de campo urgente. Registrar ocorrência no CAR. Avaliar risco de deslizamento na região.',
    model_version: 'orbital-ml-v1.2.0',
    class_percentage: 52.0,
    change_score: 0.79,
    source: 'MODIS/GIBS',
    visual_product: 'MODIS_Terra_CorrectedReflectance_TrueColor',
    tile_provider: 'NASA GIBS',
    image_url: 'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2024-08-20/250m/7/33/49.jpg',
  },
  {
    event_id: 'EVT-2024-003',
    timestamp: '2024-11-13T18:47:00Z',
    detected_class: 'vegetacao',
    risk_level: 'medio',
    analysis_confidence: 0.78,
    explanation:
      'Vegetação com índice NDVI reduzido (0.31 abaixo do histórico). Change_score de 0.45 sugere estresse hídrico ou início de supressão. Cobertura de nuvens de 18% pode afetar precisão.',
    recommendation:
      'Monitorar área nos próximos 14 dias. Cruzar com dados de pluviometria local. Agendar nova captura com menor cobertura de nuvens.',
    model_version: 'orbital-ml-v1.2.0',
    class_percentage: 61.0,
    change_score: 0.45,
    source: 'MODIS/GIBS',
    visual_product: 'MODIS_Terra_CorrectedReflectance_TrueColor',
    tile_provider: 'NASA GIBS',
    image_url: 'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2024-07-16/250m/7/31/41.jpg',
  },
  {
    event_id: 'EVT-2024-004',
    timestamp: '2024-11-12T11:22:00Z',
    detected_class: 'agua',
    risk_level: 'medio',
    analysis_confidence: 0.82,
    explanation:
      'Redução de corpo hídrico identificada em 23% da extensão histórica do lago. Dados FIRMS indicam seca prolongada na bacia. Produto visual MODIS/GIBS.',
    recommendation:
      'Acionar comitê de gestão de recursos hídricos. Verificar captações irregulares na bacia hidrográfica.',
    model_version: 'orbital-ml-v1.2.0',
    class_percentage: 23.0,
    change_score: 0.52,
    source: 'MODIS/GIBS',
    visual_product: 'MODIS_Terra_CorrectedReflectance_TrueColor',
    tile_provider: 'NASA GIBS',
    image_url: 'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2024-06-01/250m/7/37/44.jpg',
  },
  {
    event_id: 'EVT-2024-005',
    timestamp: '2024-11-11T07:05:00Z',
    detected_class: 'vegetacao',
    risk_level: 'baixo',
    analysis_confidence: 0.88,
    explanation:
      'Vegetação densa em bom estado fitossanitário. NDVI estável em 0.74. Sem alterações significativas detectadas em relação ao histórico de 90 dias. Produto visual MODIS/GIBS, qualidade 0.95.',
    recommendation:
      'Manter monitoramento de rotina. Próxima análise programada em 30 dias.',
    model_version: 'orbital-ml-v1.2.0',
    class_percentage: 88.0,
    change_score: 0.05,
    source: 'MODIS/GIBS',
    visual_product: 'MODIS_Terra_CorrectedReflectance_TrueColor',
    tile_provider: 'NASA GIBS',
    image_url: 'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2024-05-21/250m/7/31/42.jpg',
  },
  {
    event_id: 'EVT-2024-006',
    timestamp: '2024-11-10T16:38:00Z',
    detected_class: 'solo_exposto',
    risk_level: 'baixo',
    analysis_confidence: 0.85,
    explanation:
      'Solo exposto em área de pousio agrícola. Change_score de 0.12 dentro do esperado para o ciclo agrícola da região. Sem indicadores de desmatamento ilegal. Produto visual MODIS/GIBS.',
    recommendation:
      'Nenhuma ação imediata necessária. Registrar como área de manejo agrícola regular.',
    model_version: 'orbital-ml-v1.2.0',
    class_percentage: 34.0,
    change_score: 0.12,
    source: 'MODIS/GIBS',
    visual_product: 'MODIS_Terra_CorrectedReflectance_TrueColor',
    tile_provider: 'NASA GIBS',
    image_url: 'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2024-10-15/250m/7/33/50.jpg',
  },
];
