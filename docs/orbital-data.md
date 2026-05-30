# Orbital Data Ingestion — Guia Operacional

Este documento descreve como buscar imagens governamentais abertas de satélite e como o pipeline de ingestão orbital do Orbital Trust funciona.

---

## Fontes de dados

### Fonte primária — INPE Brazil Data Cube STAC

O pipeline usa o catálogo STAC do Brazil Data Cube do INPE como fonte primária para imagens Landsat e CBERS.

- **URL base:** `https://data.inpe.br/bdc/stac/v1`
- **Coleções disponíveis:**
  - `LANDSAT-8-OLI` — imagens Landsat 8 OLI
  - `CBERS4A-WPM` — imagens CBERS-4A Wide Panel Multispectral
- **Acesso:** público, sem autenticação

### Fallback — Copernicus Sentinel-2 / FIRMS

Para Sentinel-2 e FIRMS, o pipeline usa o catálogo STAC do Copernicus Data Space.

- **URL base:** `https://catalogue.dataspace.copernicus.eu/stac`
- **Coleções disponíveis:**
  - `SENTINEL-2` — imagens multiespectrais Sentinel-2
  - `FIRMS` — focos de calor NASA FIRMS
- **Acesso:** público, sem autenticação

---

## Exemplo de busca

```python
from iot.stac_client import search_scenes

scenes = search_scenes(
    bbox=[-54.0, -12.0, -52.0, -10.0],  # [west, south, east, north] em graus WGS-84
    start_date="2024-01-01",
    end_date="2024-01-31",
    source="Landsat",                    # "Sentinel-2" | "Landsat" | "FIRMS" | "INPE"
    max_cloud_score=30.0,                # cobertura de nuvens máxima em %
)
```

Parâmetros:

| Campo | Descrição | Exemplo |
|---|---|---|
| `bbox` | Bounding box em WGS-84: `[west, south, east, north]` | `[-54.0, -12.0, -52.0, -10.0]` |
| `start_date` | Data inicial ISO-8601 | `"2024-01-01"` |
| `end_date` | Data final ISO-8601 | `"2024-01-31"` |
| `source` | Fonte dos dados | `"Landsat"`, `"Sentinel-2"`, `"FIRMS"`, `"INPE"` |
| `max_cloud_score` | Cobertura de nuvens máxima (0–100%) | `30.0` |

---

## Pipeline completo de ingestão

Para executar a ingestão completa (busca → manifesto → download → pipeline IoT):

```python
from iot.orbital_ingestion import run_orbital_ingestion

payloads = run_orbital_ingestion(
    area_id="pantanal-norte",
    bbox=[-57.0, -18.0, -55.0, -16.0],
    start_date="2024-01-01",
    end_date="2024-01-31",
    source="Sentinel-2",
)
```

O retorno é uma lista de payloads IoT validados prontos para envio à API.

---

## Onde os dados são salvos

### Manifestos de cenas

Os manifestos JSON são persistidos em `data/manifests/<area_id>.json`. Cada manifesto contém a lista de cenas encontradas para uma área, com campos:

- `area_id` — identificador da área monitorada
- `generated_at` — timestamp de geração (UTC)
- `scenes` — lista com `scene_id`, `source`, `datetime`, `cloud_score`, `asset_href`

Exemplo de caminho: `data/manifests/pantanal-norte.json`

### Frames baixados

Os frames são baixados em um diretório temporário durante o processamento e não são persistidos em disco após o pipeline terminar. Se houver necessidade de manter os frames, salve o conteúdo de `data/raw/` antes do término do processo.

Os frames processados (bandas calculadas, índices NDVI, etc.) ficam em `data/processed/`.

---

## Contrato JSON IoT — NÃO ALTERAR

O payload produzido pelo pipeline IoT tem um contrato fixo que **não deve ser modificado** sem consenso de todo o time. Qualquer alteração quebra a integração com ML/API e o app mobile.

### Payload IoT → ML/API

Campos obrigatórios:

| Campo | Tipo | Descrição |
|---|---|---|
| `event_id` | string | Identificador único do evento |
| `timestamp` | string | ISO-8601 UTC do processamento |
| `area_id` | string | Identificador da área monitorada |
| `source` | string | `"Sentinel-2"`, `"Landsat"`, `"FIRMS"` ou `"INPE"` |
| `detected_class` | string | Classe detectada pelo CV |
| `class_percentage` | float | Proporção da classe na cena (0–100) |
| `change_score` | float | Score de mudança temporal (0–1) |
| `cloud_score` | float | Cobertura de nuvens (0–100) |
| `shadow_score` | float | Score de sombra (0–1) |
| `image_quality` | float | Qualidade geral da imagem (0–1) |
| `cv_confidence` | float | Confiança do modelo CV (0–1) |

### Resposta ML/API → Mobile

Campos obrigatórios:

| Campo | Tipo | Descrição |
|---|---|---|
| `event_id` | string | Mesmo `event_id` do payload de entrada |
| `risk_level` | string | `"baixo"`, `"medio"` ou `"alto"` |
| `analysis_confidence` | float | Confiança da análise ML (0–1) |
| `explanation` | string | Explicação textual do risco |
| `recommendation` | string | Ação recomendada |
| `model_version` | string | Versão do modelo usado |

> **Regra:** `risk_level` aceita apenas `"baixo"`, `"medio"` ou `"alto"`. Qualquer outro valor é inválido.

---

## Reproduzindo a ingestão localmente

```bash
# 1. Instalar dependências
pip install -r iot/requirements.txt

# 2. Executar busca e ingestão (substitua os valores conforme sua área)
python - <<'EOF'
from iot.orbital_ingestion import run_orbital_ingestion

payloads = run_orbital_ingestion(
    area_id="test-area",
    bbox=[-47.0, -15.5, -46.5, -15.0],  # região central do Brasil
    start_date="2024-06-01",
    end_date="2024-06-30",
    source="Landsat",
)
for p in payloads:
    print(p)
EOF
```

Para usar Sentinel-2 como fallback, altere `source="Sentinel-2"` e os dados serão buscados no catálogo Copernicus.
