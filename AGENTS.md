# Agente — Orbital Trust

---

## Filosofia geral

- Solução mais simples e direta. Funções em vez de classes.
- Sem Clean Architecture, DDD, Repository Pattern ou camadas de abstração desnecessárias.
- Sem logging framework ou telemetria além do básico.
- Código que um dev sênior consegue ler sem documentação.

## Estilo de código

- Linguagem: Python (pipeline IoT/CV) + TypeScript (app React Native mobile)
- Funções simples e executáveis
- Type hints em Python onde ajudam na leitura; interfaces TypeScript para todos os contratos
- Comentários curtos — o código deve se explicar

## Domínio do projeto

Orbital Trust transforma imagens orbitais abertas (Sentinel-2, Landsat) em alertas ambientais confiáveis e acionáveis. O pipeline cobre: captura e processamento de frames via OpenCV → análise de risco ML → API de integração → app React Native. O MVP usa dados abertos reais de satélite sem depender de webcam como conceito principal; a webcam/vídeo é cumprida usando sequências de frames orbitais.

## Estrutura de arquivos

```
orbital-trust/
├── iot/              # Python pipeline — OpenCV, leitura de frames, payload JSON
├── ml/               # Classificação de risco — scikit-learn ou heurísticas
├── api/              # Camada de integração — FastAPI ou Node/Express
├── mobile/           # App React Native, Expo, TypeScript
├── scripts/          # ralph.sh, implement.sh, gate.sh, prd.json
└── data/             # Frames de satélite de amostra (Sentinel-2, Landsat)
```

## Regras críticas

- O contrato JSON entre IoT e ML/API deve ser definido antes de qualquer implementação
- Campos obrigatórios no payload IoT → ML/API: `event_id`, `timestamp`, `area_id`, `source`, `detected_class`, `class_percentage`, `change_score`, `cloud_score`, `shadow_score`, `image_quality`, `cv_confidence`
- Campos obrigatórios na resposta ML/API → Mobile: `event_id`, `risk_level`, `analysis_confidence`, `explanation`, `recommendation`, `model_version`
- Nenhuma área pode alterar o formato do payload sem consenso do grupo
- `risk_level` só aceita: `baixo`, `medio`, `alto`
- Todo frame processado deve ter `source` identificado (Sentinel-2, Landsat, FIRMS, INPE)

## Gate de validação

O Ralph usa `scripts/gate.sh` para validar cada story.

- Stories Python (IoT, ML): gate `python` — py_compile + pytest
- Stories TypeScript (Mobile): gate `typescript` — tsc sem erros

Critérios mínimos de aceitação:
- Código compila / passa lint sem erros
- Testes unitários da story passam
- Sem regressão nos testes existentes

## Contexto de execução

- Provider padrão: codex → gemini → claude (fallback triplo)
- Estado do loop: `scripts/.current-provider`, `scripts/.last-story`

---

<!-- SEÇÃO GERADA AUTOMATICAMENTE PELO SKILL LEARNING — NÃO EDITE MANUALMENTE -->
## Skills ativas

As skills em `skills/active/` são injetadas como user message no início de cada sessão.
Para ver as skills pendentes de revisão: `ls skills/pending/`

<!-- END SEÇÃO GERADA -->
