import { AlertResponse } from '../types/alert';

export const mockAlerts: AlertResponse[] = [
  {
    event_id: 'EVT-2024-001',
    timestamp: '2024-11-15T14:32:00Z',
    detected_class: 'queimada',
    risk_level: 'alto',
    analysis_confidence: 0.94,
    explanation:
      'Queimada ativa detectada em 38% da área analisada. Frente de fogo em expansão com variação de 0.87 no change_score. Imagem Sentinel-2 com alta qualidade (0.92).',
    recommendation:
      'Acionar brigada de combate imediatamente. Notificar IBAMA e Defesa Civil. Interditar acesso à área.',
    model_version: 'orbital-ml-v1.2.0',
    class_percentage: 38.0,
    change_score: 0.87,
    source: 'Sentinel-2',
    image_url: 'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2024-09-30/250m/7/37/44.jpg',
  },
  {
    event_id: 'EVT-2024-002',
    timestamp: '2024-11-14T09:15:00Z',
    detected_class: 'solo_exposto',
    risk_level: 'alto',
    analysis_confidence: 0.91,
    explanation:
      'Solo exposto em 52% da área com erosão severa detectada. Change_score de 0.79 indica desmatamento recente. Fonte Landsat-8 confirmada.',
    recommendation:
      'Solicitar vistoria de campo urgente. Registrar ocorrência no CAR. Avaliar risco de deslizamento na região.',
    model_version: 'orbital-ml-v1.2.0',
    class_percentage: 52.0,
    change_score: 0.79,
    source: 'Landsat-8',
    image_url: 'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2024-08-15/250m/7/36/44.jpg',
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
    source: 'Sentinel-2',
    image_url: 'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2024-07-15/250m/7/38/44.jpg',
  },
  {
    event_id: 'EVT-2024-004',
    timestamp: '2024-11-12T11:22:00Z',
    detected_class: 'agua',
    risk_level: 'medio',
    analysis_confidence: 0.82,
    explanation:
      'Redução de corpo hídrico identificada em 23% da extensão histórica do lago. Dados FIRMS indicam seca prolongada na bacia. Source: Sentinel-2.',
    recommendation:
      'Acionar comitê de gestão de recursos hídricos. Verificar captações irregulares na bacia hidrográfica.',
    model_version: 'orbital-ml-v1.2.0',
    class_percentage: 23.0,
    change_score: 0.52,
    source: 'Sentinel-2',
    image_url: 'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2024-06-01/250m/7/37/44.jpg',
  },
  {
    event_id: 'EVT-2024-005',
    timestamp: '2024-11-11T07:05:00Z',
    detected_class: 'vegetacao',
    risk_level: 'baixo',
    analysis_confidence: 0.88,
    explanation:
      'Vegetação densa em bom estado fitossanitário. NDVI estável em 0.74. Sem alterações significativas detectadas em relação ao histórico de 90 dias. Sentinel-2, qualidade 0.95.',
    recommendation:
      'Manter monitoramento de rotina. Próxima análise programada em 30 dias.',
    model_version: 'orbital-ml-v1.2.0',
    class_percentage: 88.0,
    change_score: 0.05,
    source: 'Sentinel-2',
    image_url: 'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2024-05-10/250m/7/37/45.jpg',
  },
  {
    event_id: 'EVT-2024-006',
    timestamp: '2024-11-10T16:38:00Z',
    detected_class: 'solo_exposto',
    risk_level: 'baixo',
    analysis_confidence: 0.85,
    explanation:
      'Solo exposto em área de pousio agrícola. Change_score de 0.12 dentro do esperado para o ciclo agrícola da região. Sem indicadores de desmatamento ilegal. Fonte: Landsat-9.',
    recommendation:
      'Nenhuma ação imediata necessária. Registrar como área de manejo agrícola regular.',
    model_version: 'orbital-ml-v1.2.0',
    class_percentage: 34.0,
    change_score: 0.12,
    source: 'Landsat-9',
    image_url: 'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2024-10-15/250m/7/39/44.jpg',
  },
];
