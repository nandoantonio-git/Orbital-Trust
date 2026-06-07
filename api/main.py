import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from iot.contract import ContractSource, DetectedClass, ImageQuality, IoTPayload, RiskLevel
from ml.predict import ModelNotTrainedError, predict as ml_predict

MODEL_VERSION = "orbital-heuristic-v0.1.0"  # usado só como fallback legado


class AlertResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    timestamp: str
    detected_class: DetectedClass
    risk_level: RiskLevel
    analysis_confidence: float = Field(ge=0.0, le=1.0)
    explanation: str
    recommendation: str
    model_version: str
    class_percentage: float | None = Field(default=None, ge=0.0, le=100.0)
    change_score: float | None = Field(default=None, ge=0.0, le=1.0)
    cloud_score: float | None = Field(default=None, ge=0.0, le=1.0)
    shadow_score: float | None = Field(default=None, ge=0.0, le=1.0)
    brightness_score: float | None = Field(default=None, ge=0.0, le=1.0)
    blur_score: float | None = Field(default=None, ge=0.0, le=1.0)
    image_quality: ImageQuality | None = None
    cv_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    algorithm_version: str | None = None
    source: str | None = None
    contract_source: ContractSource | None = None


app = FastAPI(title="Orbital Trust API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    # Desenvolvimento: restringir para domínios confiáveis em produção.
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

_logger = logging.getLogger(__name__)

@app.on_event("startup")
async def _startup() -> None:
    _logger.warning(
        "CORS aberto (allow_origins=['*']) — ambiente acadêmico MVP apenas. "
        "Restringir origens antes de qualquer deploy em produção."
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "orbital-trust-ml"}


@app.post("/alerts/analyze", response_model=AlertResponse)
def analyze_alert(payload: IoTPayload) -> AlertResponse:
    try:
        result = ml_predict(payload)
        risk_level: RiskLevel = result["risk_level"]
        analysis_confidence = result["analysis_confidence"]
        explanation = result["explanation"]
        recommendation = result["recommendation"]
        model_version = result["model_version"]
    except ModelNotTrainedError:
        # Fallback heurístico enquanto o modelo não foi treinado
        risk_level = derive_risk_level(
            payload.change_score,
            payload.detected_class,
            payload.image_quality,
            payload.cv_confidence,
        )
        analysis_confidence = derive_analysis_confidence(payload.image_quality, payload.cv_confidence)
        explanation = build_explanation(payload, risk_level)
        recommendation = build_recommendation(payload.detected_class, risk_level)
        model_version = MODEL_VERSION

    return AlertResponse(
        event_id=payload.event_id,
        timestamp=payload.timestamp,
        detected_class=payload.detected_class,
        risk_level=risk_level,
        analysis_confidence=analysis_confidence,
        explanation=explanation,
        recommendation=recommendation,
        model_version=model_version,
        class_percentage=payload.class_percentage,
        change_score=payload.change_score,
        cloud_score=payload.cloud_score,
        shadow_score=payload.shadow_score,
        brightness_score=payload.brightness_score,
        blur_score=payload.blur_score,
        image_quality=payload.image_quality,
        cv_confidence=payload.cv_confidence,
        algorithm_version=payload.algorithm_version,
        source=payload.source,
        contract_source=payload.source,
    )


def derive_risk_level(
    change_score: float,
    detected_class: DetectedClass,
    image_quality: ImageQuality,
    cv_confidence: float,
) -> RiskLevel:
    class_weight = {
        "queimada": 0.25,
        "solo_exposto": 0.12,
        "baixa_visibilidade": 0.10,
        "agua": 0.06,
        "vegetacao": 0.0,
    }[detected_class]
    quality_penalty = max(0.0, 0.70 - image_quality_score(image_quality)) * 0.20
    confidence_penalty = max(0.0, 0.70 - cv_confidence) * 0.15
    score = change_score + class_weight + quality_penalty + confidence_penalty

    if score > 0.50:
        return "alto"
    if score > 0.20:
        return "medio"
    return "baixo"


def image_quality_score(image_quality: ImageQuality) -> float:
    return {"boa": 0.9, "media": 0.6, "baixa": 0.3}[image_quality]


def derive_analysis_confidence(image_quality: ImageQuality, cv_confidence: float) -> float:
    return round(max(0.0, min(1.0, (image_quality_score(image_quality) * 0.45) + (cv_confidence * 0.55))), 4)


def build_explanation(payload: IoTPayload, risk_level: RiskLevel) -> str:
    class_label = payload.detected_class.replace("_", " ")
    return (
        f"Risco {risk_level} para {class_label}: mudanca {payload.change_score:.2f}, "
        f"qualidade {payload.image_quality}, brilho {payload.brightness_score:.2f}, "
        f"desfoque {payload.blur_score:.2f} e confianca CV {payload.cv_confidence:.2f}."
    )


def build_recommendation(detected_class: DetectedClass, risk_level: RiskLevel) -> str:
    recommendations = {
        "queimada": {
            "alto": "Acionar resposta de campo para queimada e notificar autoridades ambientais.",
            "medio": "Validar foco com nova imagem e preparar equipe local.",
            "baixo": "Manter monitoramento preventivo da area.",
        },
        "solo_exposto": {
            "alto": "Priorizar vistoria para erosao, desmatamento ou obra irregular.",
            "medio": "Agendar revisita orbital e comparar historico recente.",
            "baixo": "Manter acompanhamento em ciclo regular.",
        },
        "agua": {
            "alto": "Verificar alteracao hidrica relevante com equipe responsavel.",
            "medio": "Monitorar nivel e checar eventos de cheia ou seca.",
            "baixo": "Manter monitoramento hidrico de rotina.",
        },
        "baixa_visibilidade": {
            "alto": "Reprocessar com novo frame antes de decisao operacional critica.",
            "medio": "Aguardar melhor visibilidade e repetir a analise.",
            "baixo": "Reagendar captura em ciclo regular.",
        },
        "vegetacao": {
            "alto": "Checar mudanca brusca de cobertura vegetal em campo.",
            "medio": "Comparar com serie historica e monitorar a area.",
            "baixo": "Manter monitoramento ambiental de rotina.",
        },
    }
    return recommendations[detected_class][risk_level]
