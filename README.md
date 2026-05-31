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

## Arquitetura e Contratos

O Orbital Trust utiliza uma arquitetura distribuída e desacoplada:

1.  **IoT (Edge):** Processamento de imagens orbitais/vídeo, extração de métricas de qualidade e inferência visual preliminar.
2.  **ML/API (Brain):** Recebe o payload do IoT, refina o risco ambiental e gera recomendações operacionais.
3.  **Mobile (User):** Exibe alertas, histórico e métricas de confiança.

### Contrato IoT -> ML/API

A fonte única da verdade para o contrato é o modelo Pydantic `IoTPayload` em `iot/contract.py`.

Campos obrigatórios enviados pelo pipeline IoT/CV:

```json
{
  "event_id": "UUID/String",
  "timestamp": "ISO-8601",
  "area_id": "string",
  "source": "Sentinel-2 | Landsat | FIRMS | INPE",
  "detected_class": "queimada | solo_exposto | agua | vegetacao | baixa_visibilidade",
  "class_percentage": 0-100,
  "change_score": 0-1,
  "cloud_score": 0-1,
  "shadow_score": 0-1,
  "brightness_score": 0-1,
  "blur_score": 0-1,
  "image_quality": "boa | media | baixa",
  "cv_confidence": 0-1,
  "frame_reference": "string",
  "algorithm_version": "string"
}
```

Fontes válidas para frames processados: `Sentinel-2`, `Landsat`, `FIRMS` ou `INPE`.

`tile_quality` é metadado interno opcional do pipeline para auditoria de fallback e integridade do tile. Ele não faz parte dos campos obrigatórios IoT -> ML/API e não é campo do `AlertResponse` consumido pelo Mobile.

## Instalação e Execução

As dependências de todos os módulos Python estão consolidadas no arquivo raiz.

```bash
# Instalação unificada
pip install -r requirements.txt

# Execução da Demo de Vídeo (IoT)
python3 iot/demo_video.py --input seu_video.mp4

# Execução da API
uvicorn api.main:app --reload
```

## Mobile

O aplicativo está desenvolvido em React Native com Expo SDK 52 e TypeScript.

**Telas principais:**
- **Dashboard:** Visão geral dos alertas ativos.
- **Detalhes:** Métricas profundas de qualidade e confiança.
- **Histórico:** Log local de eventos persistido via AsyncStorage.
- **Configurações:** Controle de modo de dados (API vs Mock).
- **Sobre:** Informações do projeto Orbital Trust.

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
