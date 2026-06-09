# Orbital Trust

Pipeline IoT de visão computacional que transforma frames de satélite em alertas ambientais confiáveis e acionáveis. Cada frame orbital passa por segmentação semântica com MediaPipe, detecção de classe por heurística BGR, métricas de qualidade visual e envio automático para a API FastAPI — que deriva o nível de risco e entrega o resultado no app mobile Expo em tempo real.

## Integrantes

| Nome | RM |
|---|---|
| Fernando Luiz Silva Antonio | RM555201 |
| Gustavo Ruiz Vieira Paulino | RM554779 |
| Guilherme Abe | RM554743 |
| Thomas Reichmann | RM554812 |
| Victor Dias | RM558017 |

## Estrutura do Projeto

```text
orbital-trust/
├── api/              # FastAPI: heurística de risco + store + endpoints /pipeline
├── iot/              # Pipeline Python: OpenCV, MediaPipe, payload IoT
├── ml/               # RandomForest (94% CV acc) + features + notebook
├── mobile/           # App React Native — Expo SDK 52 + TypeScript
├── tests/            # 172 testes pytest
├── scripts/          # Gates, mock data, PRD
├── data/             # Frames e manifests de satélite de amostra
├── queimada.mp4      # Vídeo de demo na raiz
└── Dockerfile        # python:3.11-bookworm, porta 8000
```

## Arquitetura do MVP

```text
queimada.mp4 (frames simulando satélite)
        |
        v
iot/demo_video.py
  ├── OpenCV          — leitura de frames + change_score
  ├── MediaPipe       — ImageSegmenter DeepLab v3 TFLite
  ├── _detect_flame_mask()  — heurística BGR de chama (threshold 8%)
  ├── quality.py      — cloud, shadow, blur, brightness, cv_confidence
  └── payload.py      — IoTPayload validado por Pydantic
        |
        v  POST /alerts/analyze
api/main.py (FastAPI)
  ├── derive_risk_level()   — heurística: change_score + class_weight + penalidades
  ├── _alerts_store         — store em memória (FIFO, cap 200)
  ├── POST /pipeline/start  — dispara demo_video.py como subprocess
  └── GET  /alerts          — polling pelo mobile
        |
        v  polling 3s
mobile/ (Expo React Native)
  ├── DashboardScreen   — botão ▶ Analisar Vídeo + alertas em tempo real
  ├── AlertDetailScreen — métricas completas + histórico AsyncStorage
  ├── HistoryScreen     — log local persistido
  └── SettingsScreen    — modo API vs Mock
```

## Bibliotecas Utilizadas

**Visão Computacional / IoT (Python)**

| Biblioteca | Uso |
|---|---|
| `opencv-python` | Leitura de vídeo, change_score, overlay visual, morfologia |
| `mediapipe` | ImageSegmenter Tasks API (DeepLab v3 TFLite) |
| `numpy` | Manipulação de máscaras e frames |
| `pydantic` | Validação de contrato IoTPayload |
| `fastapi` + `uvicorn` | API de análise e endpoints de pipeline |

**Mobile**

| Biblioteca | Uso |
|---|---|
| `expo` ~52.0.40 | Runtime React Native |
| `@react-navigation/stack` | Navegação entre telas |
| `@react-native-async-storage` | Histórico local persistido |

## Vídeo de Demonstração

https://youtu.be/UN1aaWsvnXQ

## Instalação e Execução

```bash
# Clone e entre na pasta do projeto
git clone https://github.com/nandoantonio-git/Orbital-Trust
cd Orbital-Trust

# Instalar dependências Python
pip install -r requirements.txt

# Terminal 1 — API
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — Demo de vídeo (ou acionar pelo app)
python3 iot/demo_video.py \
  --input queimada.mp4 \
  --area-id BR-MT-001 \
  --every 30 \
  --api http://localhost:8000 \
  --show

# Terminal 3 — Mobile
cd mobile
npm install
npx expo start
```

**Configurar IP do backend no mobile:**

Crie `mobile/.env` com o IP da máquina rodando a API:

```bash
EXPO_PUBLIC_ALERTS_API_MODE=api
EXPO_PUBLIC_ALERTS_BASE_URL=http://SEU-IP-LOCAL:8000
```

Para descobrir o IP local:
```bash
# macOS/Linux
ipconfig getifaddr en0

# Windows
ipconfig
```

## Controle Interativo do Demo

Enquanto a janela OpenCV estiver aberta:

| Tecla | Ação |
|---|---|
| `q` | Encerrar |
| `p` | Pausar / retomar |
| `s` | Salvar PNG do frame atual |

## Endpoints da API

| Método | Path | Descrição |
|---|---|---|
| `GET` | `/health` | Healthcheck |
| `POST` | `/alerts/analyze` | Analisa IoTPayload e gera alerta |
| `GET` | `/alerts` | Lista alertas (mais recentes primeiro) |
| `GET` | `/alerts/{event_id}` | Busca alerta por ID |
| `POST` | `/pipeline/start` | Inicia demo_video.py como subprocess |
| `POST` | `/pipeline/stop` | Encerra o pipeline |
| `GET` | `/pipeline/status` | Estado atual do pipeline |

**Exemplo — analisar payload:**

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

**Healthcheck:**

```bash
curl http://127.0.0.1:8000/health
# {"status": "ok", "service": "orbital-trust-ml"}
```

## Contrato IoTPayload

Fonte única da verdade: `iot/contract.py` (Pydantic).

```json
{
  "event_id": "string",
  "timestamp": "ISO-8601",
  "area_id": "string",
  "source": "Sentinel-2 | Landsat | FIRMS | INPE",
  "detected_class": "queimada | solo_exposto | agua | vegetacao | baixa_visibilidade",
  "class_percentage": "0.0–100.0",
  "change_score": "0.0–1.0",
  "cloud_score": "0.0–1.0",
  "shadow_score": "0.0–1.0",
  "brightness_score": "0.0–1.0",
  "blur_score": "0.0–1.0",
  "image_quality": "boa | media | baixa",
  "cv_confidence": "0.0–1.0",
  "frame_reference": "string",
  "algorithm_version": "string"
}
```

## Docker

```bash
docker build -t orbital-trust .
docker run --rm -p 8000:8000 orbital-trust
```

> **Nota:** `--show` (janela OpenCV) requer display gráfico. Em ambiente headless (Docker sem X11), omita a flag `--show` ao rodar `demo_video.py`.

## Validação

```bash
# Testes Python
python3 -m pytest tests/ -q --tb=short

# TypeScript (zero erros)
cd mobile && npx tsc --noEmit

# Gate de qualidade (Python, TypeScript ou Bash)
bash scripts/gate.sh iot/demo_video.py
bash scripts/gate.sh mobile/src/screens/DashboardScreen.tsx
```

## CORS

A API registra `CORSMiddleware` com `allow_origins=["*"]` para chamadas locais do Expo durante o desenvolvimento. Em produção, restringir para os domínios confiáveis.