# Orbital Trust

Orbital Trust e um MVP para transformar imagens orbitais abertas em alertas ambientais confiaveis e acionaveis. O pipeline usa frames de satelite reais, como Sentinel-2, Landsat e tiles publicos equivalentes, para detectar sinais de queimada, solo exposto, agua, vegetacao e baixa visibilidade antes de entregar o resultado em um app mobile Expo.

O projeto substitui a ideia de webcam por sequencias de frames orbitais: cada frame e carregado pelo pipeline IoT/CV, recebe metricas de qualidade e mudanca, vira um payload JSON padronizado e alimenta a camada de analise usada pelo app.

## Estrutura Do Projeto

```text
orbital-trust/
├── iot/              # Pipeline Python: leitura de frames, OpenCV, payload JSON
├── api/              # FastAPI: analise heuristica e AlertResponse para o mobile
├── mobile/           # App React Native com Expo e TypeScript
├── scripts/          # Ralph loop, gates e geracao de mock data real
├── data/             # Frames e manifests de satelite de amostra
└── tests/            # Testes unitarios do pipeline Python
```

Tambem existem diretorios de suporte herdados do Athena/Ralph, como `skills/`, `loops/` e `memory/`, usados para automacao de stories e aprendizado de skills.

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

Nenhuma camada deve alterar estes campos sem acordo do grupo. `risk_level` aceita apenas `baixo`, `medio` ou `alto`. `class_percentage` usa sempre percentual `0-100`, nunca proporcao `0-1`.

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
  "image_quality": 0.91,
  "cv_confidence": 0.87
}
```

Fontes validas para frames processados: `Sentinel-2`, `Landsat`, `FIRMS` ou `INPE`. O contrato implementado tambem pode incluir `frame_reference` para rastrear o arquivo ou tile usado.

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
python3 -m pip install -r requirements.txt -r requirements-dev.txt
python3 -m pip install -r iot/requirements.txt
```

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
python3 -m uvicorn api.main:app --reload
```

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
    "image_quality": 0.91,
    "cv_confidence": 0.87
  }'
```

O endpoint retorna `AlertResponse`. Enquanto nao houver modelo ML real, `risk_level` e derivado por heuristica explicita usando `change_score`, `detected_class`, `image_quality` e `cv_confidence`.

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

## Ralph E Athena

O repositorio ainda inclui o loop Ralph/Athena para automatizar stories do MVP. Esse conteudo e secundario para avaliacao do produto, mas segue util para o fluxo de implementacao.

```bash
bash scripts/ralph.sh
```

O Ralph le `scripts/prd.json`, seleciona a primeira story pendente, chama o provider configurado e executa `scripts/gate.sh` para validar a entrega. O provider ativo fica em `scripts/.current-provider`; a ultima story processada fica em `scripts/.last-story`.

Providers previstos:

| Provider | Comando  | Uso |
|----------|----------|-----|
| Codex    | `codex`  | Padrao |
| Gemini   | `gemini` | Fallback |
| Claude   | `claude` | Fallback |

Comandos uteis para automacao:

```bash
jq '.userStories[] | {id, title, passes}' scripts/prd.json
tail -f scripts/run.log
ls skills/active/
```
