"""Small IoT -> API sender used by the visual demo."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


DEFAULT_TIMEOUT_SECONDS = 2.0
DEFAULT_FALLBACK_DIR = Path("iot/outputs/failed_payloads")


def _contract_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "tile_quality"}


def _event_id(payload: dict[str, Any]) -> str:
    value = payload.get("event_id")
    if value in (None, ""):
        return "<sem event_id>"
    return str(value)


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "sem_event_id"


def save_failed_payload(
    payload: dict[str, Any],
    fallback_dir: str | Path = DEFAULT_FALLBACK_DIR,
) -> Path:
    """Persist one failed outbound payload without changing the API contract."""
    fallback_path = Path(fallback_dir)
    fallback_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = fallback_path / f"{timestamp}_{_safe_name(_event_id(payload))}.json"
    path.write_text(
        json.dumps(_contract_payload(payload), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _failure_status(exc: Exception) -> str:
    text = f"{type(exc).__name__} {exc}".lower()
    if "timeout" in text or "timed out" in text:
        return "timeout"
    if "connection" in text or "refused" in text or "offline" in text:
        return "connection_error"
    return "request_error"


def _log_failure(
    *,
    status: str,
    endpoint: str,
    event_id: str,
    fallback_path: Path,
    detail: str = "",
) -> None:
    detail_text = f" detail={detail}" if detail else ""
    print(
        "[iot-api] envio falhou "
        f"status={status} endpoint={endpoint} event_id={event_id} "
        f"fallback={fallback_path}{detail_text}",
        file=sys.stderr,
    )


def post_payload_to_api(
    api_base_url: str,
    payload: dict[str, Any],
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    fallback_dir: str | Path = DEFAULT_FALLBACK_DIR,
    post: Callable[..., Any] | None = None,
) -> dict[str, Any] | None:
    """POST one payload once; on failure, log and save a local fallback file."""
    endpoint = f"{api_base_url.rstrip('/')}/alerts/analyze"
    event_id = _event_id(payload)
    outbound = _contract_payload(payload)

    if post is None:
        try:
            import requests
        except ImportError:
            fallback_path = save_failed_payload(outbound, fallback_dir)
            _log_failure(
                status="requests_unavailable",
                endpoint=endpoint,
                event_id=event_id,
                fallback_path=fallback_path,
            )
            return None
        post = requests.post

    try:
        response = post(endpoint, json=outbound, timeout=timeout)
    except Exception as exc:
        fallback_path = save_failed_payload(outbound, fallback_dir)
        _log_failure(
            status=_failure_status(exc),
            endpoint=endpoint,
            event_id=event_id,
            fallback_path=fallback_path,
            detail=f"{type(exc).__name__}: {exc}",
        )
        return None

    if not getattr(response, "ok", False):
        fallback_path = save_failed_payload(outbound, fallback_dir)
        status_code = getattr(response, "status_code", "sem_status")
        response_text = str(getattr(response, "text", "")).replace("\n", " ")[:160]
        _log_failure(
            status=f"http_{status_code}",
            endpoint=endpoint,
            event_id=event_id,
            fallback_path=fallback_path,
            detail=response_text,
        )
        return None

    try:
        return response.json()
    except Exception as exc:
        fallback_path = save_failed_payload(outbound, fallback_dir)
        _log_failure(
            status="invalid_response",
            endpoint=endpoint,
            event_id=event_id,
            fallback_path=fallback_path,
            detail=f"{type(exc).__name__}: {exc}",
        )
        return None
