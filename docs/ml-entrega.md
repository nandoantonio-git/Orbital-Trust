# Orbital Trust
## Entrega — Machine Learning

**Documento de entrega da camada de ML: modelo treinado, contrato cumprido e integração com a API.**

---

## Resumo executivo

A camada de Machine Learning do Orbital Trust foi implementada e integrada à API. O módulo recebe o payload estruturado gerado pelo pipeline de IoT/CV, classifica o risco ambiental usando um modelo treinado com scikit-learn e devolve a resposta no formato definido no contrato de dados combinado com IoT, API e Mobile.

O modelo substitui a heurística de regras que existia anteriormente. O fluxo completo está funcionando: `frames orbitais → IoT/CV → IoTPayload → ML → AlertResponse → Mobile`.

---

## 1. Responsabilidade entregue

| Area | Responsabilidade | Status |
|---|---|---|
| Machine Learning | Receber dados estruturados do IoT; avaliar risco ambiental e confiança da análise | Entregue |
| Machine Learning | Retornar classificação de risco, explicação e recomendação | Entregue |
| Machine Learning | Garantir rastreabilidade com model_version | Entregue |

---

## 2. Fluxo implementado

```
data/frames
    ↓
iot/pipeline.py  (OpenCV — detecção de classe, qualidade, mudança)
    ↓
IoTPayload  (contrato definido em iot/contract.py)
    ↓
ml/features.py  (extração de features)
    ↓
ml/predict.py  (RandomForestClassifier treinado)
    ↓
AlertResponse  (risco, confiança, explicação, recomendação, model_version)
    ↓
Mobile
```

---

## 3. Contrato de dados — cumprimento

### Entrada recebida do IoT

| Campo | Tipo | Cumprido |
|---|---|---|
| `event_id` | string | ✓ |
| `timestamp` | ISO 8601 | ✓ |
| `area_id` | string | ✓ |
| `source` | Sentinel-2, Landsat, FIRMS, INPE | ✓ |
| `detected_class` | vegetacao, solo_exposto, agua, queimada, baixa_visibilidade | ✓ |
| `class_percentage` | float [0–100] | ✓ |
| `change_score` | float [0–1] | ✓ |
| `cloud_score` | float [0–1] | ✓ |
| `shadow_score` | float [0–1] | ✓ |
| `image_quality` | boa, media, baixa | ✓ |
| `cv_confidence` | float [0–1] | ✓ |
| `frame_reference` | string | ✓ |

### Saída devolvida para o Mobile via API

| Campo | Descrição | Cumprido |
|---|---|---|
| `event_id` | Vínculo com o evento analisado | ✓ |
| `risk_level` | baixo / medio / alto | ✓ |
| `analysis_confidence` | Confiança final [0–1] | ✓ |
| `explanation` | Motivo do alerta em linguagem simples | ✓ |
| `recommendation` | Ação sugerida por classe e nível de risco | ✓ |
| `model_version` | Rastreabilidade do modelo | ✓ (`orbital-ml-v1.0.0`) |

---

## 4. Módulo ML — estrutura entregue

| Arquivo | Função |
|---|---|
| `ml/features.py` | Converte IoTPayload em vetor de features para o modelo |
| `ml/train.py` | Gera dados de treino e treina o RandomForestClassifier |
| `ml/predict.py` | Carrega o modelo e executa a predição |
| `ml/model/classifier.joblib` | Modelo serializado pronto para uso |
| `ml/model/metadata.json` | Versão, data de treino e métricas |

### Tecnologia

- **Linguagem:** Python
- **Modelo:** RandomForestClassifier (scikit-learn)
- **Acurácia (cross-validation 5-fold):** 94,08% ± 0,61%
- **Dados de treino:** 1.200 amostras sintéticas cobrindo todos os cenários do contrato
- **API:** FastAPI — endpoint `POST /alerts/analyze`

---

## 5. Exemplos de resposta

**Caso de alto risco — queimada com mudança intensa:**

```json
{
  "event_id": "e1",
  "detected_class": "queimada",
  "risk_level": "alto",
  "analysis_confidence": 0.7968,
  "explanation": "Risco alto detectado para queimada: mudanca 0.85, cv confidence 0.91.",
  "recommendation": "Acionar resposta de campo para queimada e notificar autoridades ambientais.",
  "model_version": "orbital-ml-v1.0.0"
}
```

**Caso de baixo risco — vegetação estável:**

```json
{
  "event_id": "e2",
  "detected_class": "vegetacao",
  "risk_level": "baixo",
  "analysis_confidence": 0.8199,
  "explanation": "Risco baixo detectado para vegetacao: mudanca 0.05, cv confidence 0.92.",
  "recommendation": "Manter monitoramento ambiental de rotina.",
  "model_version": "orbital-ml-v1.0.0"
}
```

---

## 6. Como executar

```bash
# Instalar dependências ML
pip install scikit-learn pandas joblib

# Treinar o modelo (já treinado, só necessário para retreinar)
python3 -m ml.train

# Subir a API
uvicorn api.main:app --reload

# Testar via Swagger
# Abrir http://127.0.0.1:8000/docs no browser

# Rodar testes
python3 -m pytest tests/ -q --tb=short
```

---

## 7. Integração com o Mobile

O app Mobile pode consumir a API diretamente via `POST /alerts/analyze` enviando o payload no formato `IoTPayload`. A resposta já vem com todos os campos definidos no contrato: `risk_level`, `analysis_confidence`, `explanation`, `recommendation` e `model_version`.

O contrato não foi alterado — qualquer integração feita com base no documento de alinhamento funciona sem ajustes.

---

## 8. Cobertura de testes

| Área testada | Testes |
|---|---|
| Extração de features | Shape do vetor, ranges, one-hot, normalização |
| Predição ML | Chaves obrigatórias, risk_level válido, confidence no range |
| Casos extremos | Queimada crítica → alto, vegetação estável → baixo |
| Fallback | Erro claro se modelo não estiver treinado |
| API (endpoint) | 185 testes passando, contrato preservado |

---

**Contrato de dados preservado. Nenhum campo de IoTPayload ou AlertResponse foi alterado.**
