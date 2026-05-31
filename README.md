# Orbital Trust

Orbital Trust e um MVP para transformar imagens orbitais abertas em alertas ambientais confiaveis e acionaveis. O pipeline usa frames de satelite reais, como Sentinel-2, Landsat e tiles publicos equivalentes, para detectar sinais de queimada, solo exposto, agua, vegetacao e baixa visibilidade antes de entregar o resultado em um app mobile Expo.

O projeto substitui a ideia de webcam por sequencias de frames orbitais: cada frame e carregado pelo pipeline IoT/CV, recebe metricas de qualidade e mudanca, vira um payload JSON padronizado e alimenta a camada de analise usada pelo app.

## Integrantes

- Fernando Luiz Silva Antonio — RM555201
- Gustavo Ruiz Vieira Paulino — RM554779
- Guilherme Abe — RM554743
- Thomas Reichmann — RM554812
- Vitor Sobrenome — TODO: preencher RM real antes da entrega final

## Estrutura Do Projeto

```text
orbital-trust/
├── iot/              # Pipeline Python: leitura de frames, OpenCV, payload JSON
├── api/              # FastAPI: analise heuristica e AlertResponse para o mobile
├── mobile/           # App React Native com Expo e TypeScript
├── scripts/          # Gates e geracao de mock data real
├── data/             # Frames e manifests de satelite de amostra
└── tests/            # Testes unitarios do pipeline Python
```

## Arquitetura Do MVP

```text
data/frames + fontes abertas
        |
        v
iot/ - OpenCV, qualidade da imagem, score de mudanca, payload
        |
        v
ML/API - classificacao de risco e recomendacao operacional
        |
        v
mobile/ - dashboard Expo para alertas ambientais
```

O MVP atual mantem a classificacao e os mocks no proprio repositorio. A separacao do contrato JSON ja esta definida para permitir extrair uma API ou modelo ML dedicado sem quebrar o app.

## Contratos JSON

Nenhuma camada deve alterar estes campos sem acordo do grupo. A fonte unica do contrato IoT -> ML/API e o modelo Pydantic `IoTPayload` em `iot/contract.py`. `risk_level` aceita apenas `baixo`, `medio` ou `alto`. `class_percentage` usa sempre percentual `0-100`, nunca proporcao `0-1`.

### IoT -> ML/API

Campos obrigatorios enviados pelo pipeline IoT/CV:

```json
{
  "event_id": "EVT-2024-09-30-001",
  "timestamp": "2024-09-30T12:00:00Z",
  "area_id": "BR-MT-001",
  "source": "Sentinel-2",
  "detected_class": "queimada",
  "class_percentage": 42.7,
  "change_score": 0.68,
  "cloud_score": 0.04,
  "shadow_score": 0.12,
  "brightness_score": 0.46,
  "blur_score": 0.18,
  "image_quality": "boa",
  "cv_confidence": 0.87,
  "frame_reference": "frame_a.jpg>frame_b.jpg",
  "algorithm_version": "orbital-cv-v0.2.0"
}
```

Fontes validas para frames processados: `Sentinel-2`, `Landsat`, `FIRMS` ou `INPE`. `image_quality` aceita apenas `boa`, `media` ou `baixa`.

`tile_quality` e metadado interno opcional do pipeline para auditoria de fallback e integridade do tile. Ele nao faz parte dos campos obrigatorios IoT -> ML/API e nao e campo do `AlertResponse` consumido pelo Mobile. O campo fica nos payloads gerados pelo `run_pipeline`, como `data/payloads_BR-MT-001.json`, e registra `black_ratio`, `date_used`, `url_used` quando existir, `row`/`col` ou `bbox` quando disponiveis, `source` real do tile, resultado completo de `check_tile_integrity`, `detected_class` e `class_percentage`. Quando ha fallback, `tile_quality.fallback.original_rejected` guarda o tile recusado e `tile_quality.fallback.alternative_used` guarda o tile alternativo usado.

### ML/API -> Mobile

Campos obrigatorios consumidos pelo app:

```json
{
  "event_id": "EVT-2024-09-30-001",
  "risk_level": "alto",
  "analysis_confidence": 0.87,
  "explanation": "Queimada detectada em 42.7% da area analisada.",
  "recommendation": "Acionar brigada de combate e notificar autoridades ambientais.",
  "model_version": "orbital-ml-v1.2.0"
}
```

A resposta mobile pode incluir dados complementares para exibicao, como `timestamp`, `detected_class`, `class_percentage`, `change_score`, `source` e `image_url`.

`AlertResponse` nao exporta `tile_quality` diretamente. Os mocks gerados por `scripts/generate_mock_data.py` usam a qualidade do tile apenas para selecionar frames validos e publicam no app somente campos tipados do contrato mobile. Para depuracao, o mesmo script grava as evidencias dos tiles em `data/generated_mock_tile_evidence.json`; consulte esse JSON por `event_id` sem poluir a UI principal.

Nos mocks do app, `source` descreve a origem exibida do alerta. Quando `image_url` aponta para NASA GIBS com `MODIS_Terra_CorrectedReflectance_TrueColor`, a origem visual correta e `MODIS/GIBS`; o mock tambem deve preencher `visual_product` e `tile_provider`. Use `contract_source` apenas quando houver metadado confiavel ligando o alerta a uma fonte contratual do pipeline (`Sentinel-2`, `Landsat`, `FIRMS` ou `INPE`).

## Executando O Pipeline

Instale as dependencias Python usadas pelo pipeline e pelos testes:

```bash
python3 -m pip install -r iot/requirements.txt -r requirements-dev.txt
```

### Demo IoT Com Video Orbital

Execute o demo IoT/CV sobre o video de amostra `queimada.mp4`:

```bash
python3 iot/demo_video.py --input queimada.mp4
```

A saida padrao do demo e o video segmentado em:

```text
iot/outputs/demo_segmented.mp4
```

O demo processa a sequencia de frames do video, aplica segmentacao/metricas OpenCV e gera payloads no contrato IoT -> ML/API usando fonte valida do MVP.

Gere mock data real para o app a partir de tiles orbitais publicos:

```bash
python3 scripts/generate_mock_data.py
```

O script busca tiles NASA GIBS, aplica o pipeline de deteccao/qualidade/mudanca e grava `mobile/src/services/generatedMockData.ts`. Ele tambem grava `data/generated_mock_tile_evidence.json` com URL, data, row/col, integridade e resultado do detector por `event_id`. Ele precisa de acesso a internet.

Regenerar payloads JSON de amostra a partir dos frames locais de `data/`:

```bash
python3 scripts/regenerate_sample_payloads.py
```

O script executa `run_pipeline("data", "BR-MT-001", "Sentinel-2")` e grava `data/payloads_BR-MT-001.json`. Frames com `black_ratio > 0.15` sao ignorados pelo pipeline quando nao ha fallback valido; payloads mantidos incluem `tile_quality` para rastrear a qualidade do tile usado.

## Executando A API Local

Instale as dependencias Python:

```bash
python3 -m pip install -r requirements.txt -r requirements-dev.txt
```

Suba a API FastAPI:

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

A API registra `CORSMiddleware` para permitir chamadas locais do Expo/React Native durante o desenvolvimento do MVP. As origens estao liberadas com `["*"]` neste ambiente academico; em producao, restrinja para os dominios confiaveis.

Analise um payload IoT:

```bash
curl -X POST http://127.0.0.1:8000/alerts/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "EVT-2024-09-30-001",
    "timestamp": "2024-09-30T12:00:00Z",
    "area_id": "BR-MT-001",
    "source": "Sentinel-2",
    "detected_class": "queimada",
    "class_percentage": 42.7,
    "change_score": 0.68,
    "cloud_score": 0.04,
    "shadow_score": 0.12,
    "brightness_score": 0.46,
    "blur_score": 0.18,
    "image_quality": "boa",
    "cv_confidence": 0.87,
    "frame_reference": "frame_a.jpg>frame_b.jpg",
    "algorithm_version": "orbital-cv-v0.2.0"
  }'
```

O endpoint retorna `AlertResponse`. Enquanto nao houver modelo ML real, `risk_level` e derivado por heuristica explicita usando `change_score`, `detected_class`, `image_quality` e `cv_confidence`.

### Health Check

A API tambem expoe um endpoint simples para validar se o servico esta disponivel:

```bash
curl http://127.0.0.1:8000/health
```

Resposta esperada:

```json
{
  "status": "ok",
  "service": "orbital-trust-ml"
}
```

### Executando Com Docker

O microservico FastAPI tambem pode ser executado em container:

```bash
docker build -t orbital-trust .
docker run --rm -p 8000:8000 orbital-trust
```

A API ficara disponivel em `http://127.0.0.1:8000`.

## Executando O App Expo

```bash
cd mobile
npm install
npx expo start
```

Para abrir no navegador:

```bash
cd mobile
npx expo start --web
```

Tambem existe um atalho no `package.json` da raiz:

```bash
npm run mobile
```

### Configurando Backend Do Mobile

Use `mobile/.env.example` como referencia para conectar o app ao backend Java:

```bash
EXPO_PUBLIC_ALERTS_API_MODE=api
EXPO_PUBLIC_ALERTS_BASE_URL=http://SEU-IP-LOCAL:8080/api/v1
```

Substitua `SEU-IP-LOCAL` pelo IP da maquina que esta executando o backend em desenvolvimento. O arquivo `mobile/.env` deve conter os valores reais locais e nao deve ser commitado.

## Validacao

Comandos principais de validacao do MVP:

```bash
python3 -m pytest tests/ -q --tb=short
npx tsc --noEmit
bash scripts/gate.sh <target>
```

Exemplos:

```bash
bash scripts/gate.sh iot/pipeline.py
bash scripts/gate.sh mobile/src/screens/DashboardScreen.tsx
bash scripts/gate.sh scripts/gate.sh
```

O gate detecta o tipo pelo alvo: Python roda `py_compile` e pytest, TypeScript roda `npx tsc --noEmit`, e Bash roda `bash -n`.

## Pendencias Academicas

- Video da disciplina: pendente de gravacao/publicacao final.
- Notebook ML: `notebooks/orbital_trust_ml.ipynb` existe no repositorio; revisar execucao completa e outputs antes da entrega final.
- RM do Vitor: pendente de confirmacao no cadastro do grupo.
