import logging
import subprocess
import threading
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from iot.contract import ContractSource, DetectedClass, ImageQuality, IoTPayload, RiskLevel

_logger = logging.getLogger(__name__)

MODEL_VERSION = "orbital-heuristic-v0.1.0"

# caminho do projeto (um nível acima de api/)
PROJECT_ROOT = Path(__file__).resolve().parents[1]


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


# =============================================================================
#  STORE DE ALERTAS
# =============================================================================

_alerts_store: list[AlertResponse] = []
_store_lock = Lock()
MAX_STORE = 200


# =============================================================================
#  ESTADO DO PIPELINE
# =============================================================================

class _PipelineState:
    def __init__(self) -> None:
        self.lock = Lock()
        self.process: subprocess.Popen | None = None
        self.running: bool = False
        self.payload_count: int = 0
        self.last_frame: int = 0
        self.error: str | None = None

    def increment_payload(self) -> None:
        with self.lock:
            self.payload_count += 1

    def set_last_frame(self, frame: int) -> None:
        with self.lock:
            self.last_frame = frame


_pipeline = _PipelineState()


def _watch_pipeline(proc: subprocess.Popen) -> None:
    """Thread que aguarda o processo terminar e atualiza o estado."""
    proc.wait()
    with _pipeline.lock:
        _pipeline.running = False
        _pipeline.process = None
        if proc.returncode not in (0, -15):  # -15 = SIGTERM (kill normal)
            _pipeline.error = f"processo terminou com código {proc.returncode}"


# =============================================================================
#  APP
# =============================================================================

app = FastAPI(title="Orbital Trust API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "orbital-trust-ml"}


@app.post("/alerts/analyze", response_model=AlertResponse)
def analyze_alert(payload: IoTPayload) -> AlertResponse:
    risk_level = derive_risk_level(
        payload.change_score,
        payload.detected_class,
        payload.image_quality,
        payload.cv_confidence,
    )

    alert = AlertResponse(
        event_id=payload.event_id,
        timestamp=payload.timestamp,
        detected_class=payload.detected_class,
        risk_level=risk_level,
        analysis_confidence=derive_analysis_confidence(
            payload.image_quality,
            payload.cv_confidence,
        ),
        explanation=build_explanation(payload, risk_level),
        recommendation=build_recommendation(payload.detected_class, risk_level),
        model_version=MODEL_VERSION,
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

    with _store_lock:
        _alerts_store.append(alert)
        if len(_alerts_store) > MAX_STORE:
            _alerts_store.pop(0)

    _pipeline.increment_payload()

    return alert


@app.get("/alerts", response_model=list[AlertResponse])
def list_alerts() -> list[AlertResponse]:
    with _store_lock:
        return list(reversed(_alerts_store))


@app.get("/alerts/{event_id}", response_model=AlertResponse)
def get_alert(event_id: str) -> AlertResponse:
    with _store_lock:
        for alert in reversed(_alerts_store):
            if alert.event_id == event_id:
                return alert
    raise HTTPException(status_code=404, detail=f"Alert '{event_id}' not found")


# =============================================================================
#  PIPELINE ENDPOINTS
# =============================================================================

class PipelineStartRequest(BaseModel):
    video: str = "queimada.mp4"
    area_id: str = "BR-MT-001"
    every: int = Field(default=30, ge=1)


class PipelineStatusResponse(BaseModel):
    running: bool
    payload_count: int
    last_frame: int
    error: str | None = None


@app.post("/pipeline/start", response_model=PipelineStatusResponse)
def pipeline_start(req: PipelineStartRequest) -> PipelineStatusResponse:
    with _pipeline.lock:
        if _pipeline.running:
            return PipelineStatusResponse(
                running=True,
                payload_count=_pipeline.payload_count,
                last_frame=_pipeline.last_frame,
                error=None,
            )

        video_path = PROJECT_ROOT / req.video
        if not video_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Video nao encontrado: {req.video}",
            )

        cmd = [
            "python3",
            str(PROJECT_ROOT / "iot" / "demo_video.py"),
            "--input", str(video_path),
            "--area-id", req.area_id,
            "--every", str(req.every),
            "--api", "http://localhost:8000",
            "--show",
        ]

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Falha ao iniciar pipeline: {exc}",
            )

        _pipeline.process = proc
        _pipeline.running = True
        _pipeline.payload_count = 0
        _pipeline.last_frame = 0
        _pipeline.error = None

        thread = threading.Thread(target=_watch_pipeline, args=(proc,), daemon=True)
        thread.start()

    return PipelineStatusResponse(
        running=True,
        payload_count=0,
        last_frame=0,
        error=None,
    )


@app.post("/pipeline/stop")
def pipeline_stop() -> dict[str, str]:
    with _pipeline.lock:
        if _pipeline.process and _pipeline.running:
            _pipeline.process.terminate()
            return {"status": "stopped"}
    return {"status": "not_running"}


@app.get("/pipeline/status", response_model=PipelineStatusResponse)
def pipeline_status() -> PipelineStatusResponse:
    with _pipeline.lock:
        return PipelineStatusResponse(
            running=_pipeline.running,
            payload_count=_pipeline.payload_count,
            last_frame=_pipeline.last_frame,
            error=_pipeline.error,
        )


# =============================================================================
#  FUNÇÕES AUXILIARES
# =============================================================================

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