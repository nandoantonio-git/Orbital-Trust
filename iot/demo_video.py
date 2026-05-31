#!/usr/bin/env python3
"""
demo_video.py — Orbital Trust: análise ambiental em tempo real sobre vídeo.

Integra:
  1. MediaPipe Image Segmentation — segmenta cena em zonas (vegetação / ativo)
  2. OpenCV change detection     — change_score quadro a quadro
  3. Pipeline IoT existente      — detect_class, quality_metrics, build_payload
  4. POST opcional para a API    — /alerts/analyze → AlertResponse

Uso:
    # instalação
    pip install mediapipe requests

    # executar
    python3 iot/demo_video.py --input queimada.mp4
    python3 iot/demo_video.py --input desmate.mp4 --api http://localhost:8000 --every 60
    python3 iot/demo_video.py --input video.mp4 --output iot/outputs/saida_processada.mp4

Teclas durante execução:
    q  — sair
    p  — pausar / retomar
    s  — salvar frame atual como PNG
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.error import URLError
from urllib.request import urlretrieve

import cv2
import numpy as np

# ── project root no path ──────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from iot.detector import detect_class
from iot.quality import compute_quality_metrics
from iot.payload import build_payload
from iot.api_client import post_payload_to_api
from iot.visual_fallback import (
    fallback_detector_result,
    fallback_quality_result,
    log_visual_inference_error,
    penalize_quality_for_fallback,
)


# =============================================================================
#  CONFIGURAÇÃO DO MEDIAPIPE
# =============================================================================

DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "models" / "deeplab_v3.tflite"
DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent / "outputs" / "demo_segmented.mp4"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/image_segmenter/"
    "deeplab_v3/float32/1/deeplab_v3.tflite"
)


def _die(message: str) -> None:
    print(f"[demo_video] ERRO: {message}", file=sys.stderr)
    raise SystemExit(1)


def _ensure_model(model_path: Path) -> Path:
    """Garante que o modelo local exista, baixando o padrão quando necessário."""
    if model_path.exists():
        return model_path

    DEFAULT_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[demo_video] Modelo não encontrado: {model_path}")
    print(f"[demo_video] Baixando modelo MediaPipe Tasks para: {model_path}")

    try:
        urlretrieve(MODEL_URL, model_path)
    except (OSError, URLError) as exc:
        if model_path.exists():
            model_path.unlink()
        _die(
            "falha ao baixar o modelo .tflite. "
            f"Baixe manualmente de {MODEL_URL} e salve em {model_path}. "
            f"Detalhe: {exc}"
        )

    if not model_path.exists() or model_path.stat().st_size == 0:
        _die(
            "download do modelo terminou sem gerar um arquivo válido. "
            f"Baixe manualmente de {MODEL_URL} e salve em {model_path}."
        )

    return model_path


def _setup_segmenter(model_path: Path) -> Any:
    """Carrega o MediaPipe ImageSegmenter pela Tasks API."""
    model_path = _ensure_model(model_path)

    try:
        from mediapipe.tasks.python import BaseOptions
        from mediapipe.tasks.python.vision import (
            ImageSegmenter,
            ImageSegmenterOptions,
            RunningMode,
        )
    except ImportError as exc:
        _die(
            "MediaPipe Tasks API não está disponível. "
            "Instale a dependência com: pip install mediapipe. "
            f"Detalhe: {exc}"
        )

    try:
        options = ImageSegmenterOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=RunningMode.VIDEO,
            output_category_mask=True,
        )
        segmenter = ImageSegmenter.create_from_options(options)
    except Exception as exc:
        _die(
            "falha ao carregar o modelo MediaPipe ImageSegmenter. "
            f"Confirme que {model_path} é um modelo .tflite válido. "
            f"Detalhe: {exc}"
        )

    print(f"[demo_video] MediaPipe Tasks: ImageSegmenter carregado ({model_path})")
    return segmenter


def _segment_frame(
    segmenter: Any,
    frame_rgb: np.ndarray,
    timestamp_ms: int,
) -> np.ndarray:
    """
    Retorna máscara float32 (H, W) normalizada 0.0–1.0.

    DeepLabV3: pixels de vegetação (classe 16) = 1.0, resto = 0.0.
    """
    import mediapipe

    mp_image = mediapipe.Image(image_format=mediapipe.ImageFormat.SRGB, data=frame_rgb)
    result = segmenter.segment_for_video(mp_image, timestamp_ms)
    if result.category_mask is None:
        raise RuntimeError("MediaPipe não retornou category_mask")

    cat = result.category_mask.numpy_view()
    # Classe 16 = plant/vegetation no Pascal VOC.
    return (cat == 16).astype(np.float32)


def _segment_frame_with_fallback(
    segmenter: Any,
    frame_rgb: np.ndarray,
    timestamp_ms: int,
    frame_reference: str,
) -> tuple[np.ndarray, bool]:
    try:
        return _segment_frame(segmenter, frame_rgb, timestamp_ms), False
    except Exception as exc:
        log_visual_inference_error("segmentation", frame_reference, exc)
        h, w = frame_rgb.shape[:2]
        return np.ones((h, w), dtype=np.float32), True


# =============================================================================
#  PRÉVIA VISUAL NÃO-OFICIAL
# =============================================================================

_CLASS_WEIGHT = {
    "queimada":          0.25,
    "solo_exposto":      0.12,
    "baixa_visibilidade":0.10,
    "agua":              0.06,
    "vegetacao":         0.00,
}

def _derive_visual_preview(change_score: float, detected_class: str) -> str:
    """Prévia visual para overlay; a decisão oficial de risco fica na API/ML."""
    score = change_score + _CLASS_WEIGHT.get(detected_class, 0.0)
    if score > 0.50:
        return "alto"
    if score > 0.20:
        return "medio"
    return "baixo"


# =============================================================================
#  OVERLAY VISUAL
# =============================================================================

_CLASS_PT = {
    "queimada":           "Queimada",
    "solo_exposto":       "Solo Exposto",
    "vegetacao":          "Vegetação",
    "agua":               "Água",
    "baixa_visibilidade": "Baixa Visibilidade",
}

_VISUAL_PREVIEW_COLOR = {
    "alto":  (40,  40,  220),   # BGR vermelho
    "medio": (30, 165,  255),   # BGR laranja
    "baixo": (50,  200,  50),   # BGR verde
}

_VISUAL_PREVIEW_PT = {
    "alto": "ALTO",
    "medio": "MÉDIO",
    "baixo": "BAIXO",
}


def _draw_overlay(
    frame: np.ndarray,
    mask: np.ndarray,
    detected_class: str,
    visual_preview: str,
    change_score: float,
    class_pct: float,
    confidence: float,
    frame_num: int,
    payload_count: int,
    seg_mode: str,
) -> np.ndarray:
    """Monta display com overlay de segmentação e painel de métricas IoT."""
    display = frame.copy()
    h, w = display.shape[:2]

    # ── segmentação colorida ──────────────────────────────────────────────────
    preview_color = _VISUAL_PREVIEW_COLOR.get(visual_preview, (120, 120, 120))
    active = (mask > 0.45).astype(np.uint8)

    tint = np.zeros_like(display)
    tint[active == 1] = preview_color
    display = cv2.addWeighted(display, 0.72, tint, 0.28, 0)

    # contorno da região ativa
    contours, _ = cv2.findContours(active * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(display, contours, -1, preview_color, 2)

    # ── barra superior ────────────────────────────────────────────────────────
    cv2.rectangle(display, (0, 0), (w, 84), (18, 18, 18), -1)
    cv2.rectangle(display, (0, 0), (w, 84), (50, 50, 50), 1)

    cv2.putText(
        display, "ORBITAL TRUST  —  Monitoramento Ambiental em Tempo Real",
        (12, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (200, 200, 200), 1, cv2.LINE_AA,
    )
    cv2.putText(
        display, f"Classe: {_CLASS_PT.get(detected_class, detected_class)}  ({class_pct:.0f}%)",
        (12, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (255, 255, 255), 2, cv2.LINE_AA,
    )
    cv2.putText(
        display, f"Prévia visual (não oficial): {_VISUAL_PREVIEW_PT.get(visual_preview, visual_preview)}",
        (12, 76), cv2.FONT_HERSHEY_SIMPLEX, 0.62, preview_color, 2, cv2.LINE_AA,
    )

    # badge MediaPipe
    badge_x = w - 230
    cv2.putText(
        display, f"MediaPipe [{seg_mode}]",
        (badge_x, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (120, 220, 120), 1, cv2.LINE_AA,
    )

    # ── barra inferior ────────────────────────────────────────────────────────
    cv2.rectangle(display, (0, h - 46), (w, h), (18, 18, 18), -1)
    cv2.rectangle(display, (0, h - 46), (w, h), (50, 50, 50), 1)

    metrics = (
        f"change_score: {change_score:.3f}   "
        f"confidence: {confidence:.2f}   "
        f"payloads gerados: {payload_count}   "
        f"frame: {frame_num}"
    )
    cv2.putText(
        display, metrics,
        (12, h - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (160, 160, 160), 1, cv2.LINE_AA,
    )

    # ── barra de change_score ─────────────────────────────────────────────────
    bar_y = h - 8
    bar_w = int(w * min(change_score * 2.5, 1.0))
    bar_color = (
        (40, 40, 220) if change_score > 0.25
        else (30, 165, 255) if change_score > 0.10
        else (50, 200, 50)
    )
    cv2.rectangle(display, (0, bar_y - 4), (bar_w, bar_y + 4), bar_color, -1)

    return display


# =============================================================================
#  MAIN
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Orbital Trust — demo de vídeo com MediaPipe + OpenCV"
    )
    parser.add_argument("--input",  "-i", required=True,
                        help="Vídeo de entrada (mp4, avi, mov…)")
    parser.add_argument("--area-id", default="demo-video-area",
                        help="ID da área monitorada (padrão: demo-video-area)")
    parser.add_argument("--every",  type=int, default=30,
                        help="Gerar payload IoT a cada N frames (padrão: 30)")
    parser.add_argument("--api",    default=None,
                        help="URL da API FastAPI, ex: http://localhost:8000")
    parser.add_argument("--output", "-o", default=str(DEFAULT_OUTPUT_PATH),
                        help=f"Vídeo processado de saída (padrão: {DEFAULT_OUTPUT_PATH})")
    parser.add_argument("--model",  default=str(DEFAULT_MODEL_PATH),
                        help=f"Modelo .tflite do MediaPipe Tasks (padrão: {DEFAULT_MODEL_PATH})")
    parser.add_argument("--show",   action="store_true",
                        help="Exibir janela OpenCV durante o processamento")
    parser.add_argument("--save",   default=None,
                        help=argparse.SUPPRESS)
    parser.add_argument("--speed",  type=float, default=1.0,
                        help="Velocidade de reprodução (padrão: 1.0)")
    parser.add_argument("--resize", type=int, default=1280,
                        help="Redimensionar para este lado máximo (padrão: 1280)")
    args = parser.parse_args()

    if args.every <= 0:
        _die("--every deve ser maior que zero")
    if args.speed <= 0:
        _die("--speed deve ser maior que zero")
    if args.resize <= 0:
        _die("--resize deve ser maior que zero")

    input_path = Path(args.input)
    if not input_path.exists():
        _die(f"arquivo de entrada não encontrado: {input_path}")

    output_path = Path(args.save or args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    model_path = Path(args.model)

    # ── abrir vídeo ───────────────────────────────────────────────────────────
    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        _die(f"não foi possível abrir o vídeo: {input_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if orig_w <= 0 or orig_h <= 0:
        cap.release()
        _die(f"não foi possível ler dimensões do vídeo: {input_path}")

    # dimensões de processamento
    scale = min(args.resize / max(orig_w, orig_h), 1.0)
    proc_w = int(orig_w * scale)
    proc_h = int(orig_h * scale)

    print(f"[demo_video] {input_path}")
    print(f"             {orig_w}x{orig_h} → proc {proc_w}x{proc_h}  |  {fps:.1f} fps  |  {total} frames")

    # ── MediaPipe ─────────────────────────────────────────────────────────────
    segmenter = _setup_segmenter(model_path)

    # ── video writer ──────────────────────────────────────────────────────────
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (proc_w, proc_h))
    if not writer.isOpened():
        cap.release()
        try:
            segmenter.close()
        except Exception:
            pass
        _die(f"não foi possível criar o vídeo de saída: {output_path}")
    print(f"[demo_video] Salvando em: {output_path}")

    # ── estado ────────────────────────────────────────────────────────────────
    prev_gray: Optional[np.ndarray] = None
    frame_num     = 0
    payload_count = 0
    last_class    = "vegetacao"
    last_preview  = "baixo"
    last_change   = 0.0
    last_class_pct= 0.0
    last_conf     = 0.0
    paused        = False
    delay_ms      = max(1, int(1000 / fps / args.speed))

    print(f"[demo_video] Iniciando — payload a cada {args.every} frames  |  teclas: q=sair  p=pausar  s=captura")
    print()

    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                print("[demo_video] Fim do vídeo.")
                break

            frame_num += 1
            timestamp_ms = int(frame_num * 1000.0 / fps)

            # redimensionar
            if scale < 1.0:
                frame = cv2.resize(frame, (proc_w, proc_h))

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            frame_reference = f"video_frame_{frame_num:06d}"

            # ── 1. MediaPipe segmentation ─────────────────────────────────────
            mask, segmentation_fallback = _segment_frame_with_fallback(
                segmenter,
                frame_rgb,
                timestamp_ms,
                frame_reference,
            )
            current_seg_mode = "fallback" if segmentation_fallback else "tasks"

            # ── 2. Change score via diff de escala de cinza ───────────────────
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
            if prev_gray is not None:
                change_score = float(np.abs(gray - prev_gray).mean() / 255.0)
                change_score = round(min(max(change_score, 0.0), 1.0), 6)
            else:
                change_score = 0.0
            prev_gray = gray

            # ── 3. IoT detector + quality ─────────────────────────────────────
            visual_fallback = segmentation_fallback
            try:
                detected = detect_class(frame)
            except Exception as exc:
                log_visual_inference_error("detector", frame_reference, exc)
                detected = fallback_detector_result()
                visual_fallback = True

            try:
                quality = compute_quality_metrics(frame)
            except Exception as exc:
                log_visual_inference_error("quality", frame_reference, exc)
                quality = fallback_quality_result()
                visual_fallback = True

            if visual_fallback:
                quality = penalize_quality_for_fallback(quality)

            preview  = _derive_visual_preview(change_score, detected["detected_class"])

            last_class    = detected["detected_class"]
            last_preview  = preview
            last_change   = change_score
            last_class_pct= detected["class_percentage"]
            last_conf     = quality["cv_confidence"]

            # ── 4. Gerar payload IoT a cada N frames ──────────────────────────
            if frame_num % args.every == 0:
                payload = build_payload(
                    event_id=str(uuid.uuid4()),
                    area_id=args.area_id,
                    source="FIRMS",          # fonte válida do contrato
                    detector_result=detected,
                    quality_result=quality,
                    change_score=change_score,
                    frame_reference=frame_reference,
                )
                payload_count += 1

                ts = datetime.now().strftime("%H:%M:%S")
                print(
                    f"  [{ts}] frame {frame_num:5d}"
                    f"  classe={last_class:18s}"
                    f"  {last_class_pct:5.1f}%"
                    f"  change={change_score:.3f}"
                    f"  previa_visual={preview:6s}"
                    f"  #{payload_count}"
                )

                if args.api:
                    a = post_payload_to_api(args.api, payload)
                    if a:
                        print(
                            f"           → API risk={a.get('risk_level'):6s}"
                            f"  conf={a.get('analysis_confidence', 0):.2f}"
                        )

            # ── 5. Overlay + exibição ─────────────────────────────────────────
            display = _draw_overlay(
                frame, mask,
                last_class, last_preview, last_change,
                last_class_pct, last_conf,
                frame_num, payload_count, current_seg_mode,
            )

            writer.write(display)

            if args.show:
                cv2.imshow("Orbital Trust — Monitoramento Ambiental", display)

        # ── teclas ────────────────────────────────────────────────────────────
        if args.show:
            key = cv2.waitKey(delay_ms) & 0xFF
            if key == ord("q"):
                print("\n[demo_video] Encerrado pelo usuário.")
                break
            elif key == ord("p"):
                paused = not paused
                print(f"[demo_video] {'Pausado' if paused else 'Retomado'}")
            elif key == ord("s") and "display" in locals():
                fname = f"capture_frame{frame_num:06d}.png"
                cv2.imwrite(fname, display)
                print(f"[demo_video] Captura salva: {fname}")

    # ── limpeza ───────────────────────────────────────────────────────────────
    cap.release()
    if writer:
        writer.release()
    if args.show:
        cv2.destroyAllWindows()

    try:
        segmenter.close()
    except Exception:
        pass

    print()
    print("═" * 55)
    print(f"  Frames processados : {frame_num}")
    print(f"  Payloads gerados   : {payload_count}")
    print(f"  Última classe      : {last_class}")
    print(f"  Última prévia      : {last_preview} (visual, não oficial)")
    print(f"  Último change_score: {last_change:.4f}")
    print("═" * 55)


if __name__ == "__main__":
    main()
