---
name: contrato-inter-camadas
description: "Use ao implementar ou modificar qualquer código que produza ou consuma payloads entre camadas do pipeline (IoT→ML/API ou ML/API→Mobile)"
user-invocable: false
---

# Validação de Contrato Inter-Camadas

**Trigger:** Sempre que você for implementar ou alterar código que toca o limite entre camadas — pipeline IoT gerando payloads, ML/API processando dados, ou app mobile consumindo respostas da API.

## O que fazer

**Antes de escrever qualquer código**, abra `AGENTS.md` e localize os campos obrigatórios do contrato relevante:

- **IoT → ML/API:** `event_id`, `timestamp`, `area_id`, `source`, `detected_class`, `class_percentage`, `change_score`, `cloud_score`, `shadow_score`, `image_quality`, `cv_confidence`
- **ML/API → Mobile:** `event_id`, `risk_level`, `analysis_confidence`, `explanation`, `recommendation`, `model_version`

**Durante a implementação**, valide cada campo explicitamente:

1. Todos os campos obrigatórios estão presentes na estrutura/dict/interface?
2. `risk_level` usa exatamente um dos valores permitidos: `"baixo"`, `"medio"` ou `"alto"`?
3. `source` identifica a origem correta: `Sentinel-2`, `Landsat`, `FIRMS` ou `INPE`?
4. Interfaces TypeScript no mobile refletem o contrato ML/API → Mobile sem campos extras não acordados?

**Após implementar**, rode o gate do arquivo modificado antes de reportar conclusão:

```bash
bash scripts/gate.sh <arquivo_ou_diretorio>
```

O gate detecta o tipo automaticamente (`.py` → pytest + py_compile; `.ts`/`.tsx` → tsc). Gate com exit 1 = story não concluída.

## O que evitar

- Adicionar campos novos ao payload sem consenso do grupo — mesmo que "só para facilitar o desenvolvimento"
- Usar aliases de `risk_level` fora do enum (`"high"`, `"critical"`, `"low"` são inválidos e quebram o mobile)
- Reportar a story como concluída sem rodar o gate e confirmar `gate: OK`
- Omitir campos obrigatórios com a justificativa de que "ainda não são usados" — o contrato é total, não parcial
- Assumir que uma interface TypeScript existente está correta sem verificar contra os campos do AGENTS.md
