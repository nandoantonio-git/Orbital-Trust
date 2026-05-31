# PRD: Satellite Tile Quality Filter

## Introduction

Tiles MODIS/GIBS retornados pelo pipeline IoT frequentemente contêm áreas pretas onde o satélite não cobriu aquele tile na passagem orbital. Isso contamina o pipeline de visão computacional com frames inválidos e resulta em imagens quebradas no app mobile. Este filtro verifica a integridade de cada tile no pipeline Python antes de processá-lo — e se o tile falhar, busca automaticamente um tile de data alternativa (±3 dias) até encontrar um aceitável.

## Goals

- Rejeitar tiles com cobertura de dados insuficiente (razão de pixels pretos > 15%)
- Substituir tiles rejeitados por tiles de datas próximas automaticamente, sem intervenção humana
- Garantir que todo frame processado pelo pipeline tenha cobertura válida de satélite
- Não alterar a interface pública de `run_pipeline` — a mudança é transparente para quem chama

## User Stories

### US-001: Função de verificação de integridade do tile
**Description:** As a developer, I want a function that measures the black pixel ratio of a frame so that the pipeline can decide if the tile has valid satellite coverage.

**Acceptance Criteria:**
- [ ] Arquivo `iot/tile_quality.py` criado
- [ ] Função `check_tile_integrity(frame: np.ndarray) -> dict` retorna `{'passes': bool, 'black_ratio': float, 'reason': str}`
- [ ] `black_ratio` = proporção de pixels onde todos os canais BGR são <= 10 (preto absoluto)
- [ ] `passes = True` quando `black_ratio <= 0.15` (máximo 15% de pixels pretos)
- [ ] `passes = False` quando `black_ratio > 0.15`
- [ ] `reason` descreve o motivo: ex. `"black_ratio=0.42 exceeds threshold 0.15"` ou `"ok"`
- [ ] Teste unitário: frame totalmente preto → `passes=False`, `black_ratio=1.0`
- [ ] Teste unitário: frame totalmente colorido → `passes=True`, `black_ratio=0.0`
- [ ] Teste unitário: frame com exatamente 15% de pixels pretos → `passes=True`
- [ ] Teste unitário: frame com 16% de pixels pretos → `passes=False`
- [ ] Typecheck passes

### US-002: Buscador de tile alternativo por data
**Description:** As a developer, I want a function that fetches an alternative tile for a nearby date when the original tile fails quality check, so the pipeline always has a valid frame to process.

**Acceptance Criteria:**
- [ ] Arquivo `iot/tile_fetcher.py` criado
- [ ] Função `fetch_best_tile(base_url_template: str, base_date: str, row: int, col: int, max_days_offset: int = 3) -> tuple[np.ndarray | None, str | None]` retorna `(frame, date_used)` ou `(None, None)` se todas as datas falharem
- [ ] Tenta datas em ordem: `base_date`, `base_date - 1d`, `base_date + 1d`, `base_date - 2d`, `base_date + 2d`, `base_date - 3d`, `base_date + 3d`
- [ ] Para cada data: faz download do tile via HTTPS, chama `check_tile_integrity`, retorna o primeiro que passar
- [ ] Usa `ssl` + `certifi` para HTTPS (padrão já estabelecido no projeto em `stac_client.py`)
- [ ] Se nenhum tile passar em todas as tentativas, retorna `(None, None)` sem lançar exceção
- [ ] Loga cada tentativa com `print(f"[tile_fetcher] {date}: black_ratio={ratio:.2f} {'OK' if passes else 'SKIP'}")`
- [ ] Teste unitário com mock HTTP: simula tile preto nas 2 primeiras tentativas, colorido na 3ª → retorna frame da 3ª
- [ ] Typecheck passes

### US-003: Integrar filtro de qualidade no pipeline principal
**Description:** As a developer, I want the main IoT pipeline to automatically replace bad tiles with quality-checked alternatives so that every payload generated has valid satellite data.

**Acceptance Criteria:**
- [ ] `iot/pipeline.py` modificado — antes de processar cada frame, chama `check_tile_integrity`
- [ ] Se o frame falhar (`passes=False`): chama `fetch_best_tile` com os parâmetros do tile original para obter substituto
- [ ] Se `fetch_best_tile` retornar `None`: o frame é ignorado (não gera payload) e um `print(f"[pipeline] {filename}: sem tile válido disponível, ignorando")` é emitido
- [ ] Se `fetch_best_tile` retornar um frame alternativo: usa esse frame no lugar do original e atualiza `frame_reference` para indicar a data usada (ex: `"frame_mt_20240601.jpg>alt:2024-06-03"`)
- [ ] A assinatura de `run_pipeline(frames_folder, area_id, source)` permanece idêntica — sem breaking changes
- [ ] Payloads gerados incluem campo `tile_quality: {'black_ratio': float, 'date_used': str}` com metadados da seleção
- [ ] Teste de integração: pasta com 1 tile preto e 1 tile colorido → gera apenas 1 payload (do tile colorido)
- [ ] Typecheck passes

## Functional Requirements

- FR-1: `check_tile_integrity` classifica um tile como inválido quando mais de 15% dos pixels são pretos (todos canais BGR ≤ 10)
- FR-2: Quando um tile falha, `fetch_best_tile` tenta até 7 datas alternativas (±3 dias em ordem de proximidade)
- FR-3: O pipeline descarta silenciosamente frames sem tile válido — não lança exceção, apenas loga e continua
- FR-4: O campo `frame_reference` no payload indica se foi usada uma data alternativa
- FR-5: Todo o processamento de qualidade ocorre no módulo IoT Python — o app mobile não é alterado
- FR-6: O threshold de 15% é definido como constante `BLACK_RATIO_THRESHOLD = 0.15` em `tile_quality.py` para facilitar ajuste futuro

## Non-Goals

- Não filtrar tiles por cobertura de nuvens (isso já é tratado pelo `cloud_score` em `quality.py`)
- Não modificar o app mobile ou o mock data
- Não implementar cache de tiles válidos entre execuções
- Não suportar fontes além de NASA GIBS WMTS nesta iteração
- Não alterar tiles já baixados em `data/` — o filtro atua apenas no momento do download/processamento

## Technical Considerations

- Reutilizar o padrão SSL/certifi já estabelecido em `iot/stac_client.py` (linhas 1-7)
- A URL template do NASA GIBS segue o padrão: `https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/{date}/250m/7/{row}/{col}.jpg`
- `fetch_best_tile` recebe o template de URL como parâmetro para não hardcodar a fonte
- Parsing de datas usa `datetime` da stdlib — sem dependências externas novas
- `tile_fetcher.py` usa `urllib.request` (já usado em `stac_client.py`) — não adicionar `requests`

## Success Metrics

- 0 payloads gerados com `black_ratio > 0.15` após a implementação
- Pipeline roda sem erros em pasta com tiles parcialmente pretos
- Taxa de sucesso do `fetch_best_tile` ≥ 80% para regiões com dados históricos disponíveis

## Open Questions

- O threshold de 15% pode ser muito restritivo para regiões polares (mais áreas sem dados). Ajustar se necessário após testes com dados reais.
- Adicionar `tile_quality` ao contrato do `IoTPayload` TypeScript em iteração futura?
