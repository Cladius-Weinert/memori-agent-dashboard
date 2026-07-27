"""Ship logs and events to Elastic Cloud (Observability)."""
from __future__ import annotations

import base64
import os
from datetime import datetime, timezone
from typing import Any

import httpx

_INDEX = "logs-opsora.mobile-default"
_SERVICE = os.getenv("ELASTIC_APM_SERVICE_NAME", "memori-agent-api")


def _api_key() -> str | None:
    return os.getenv("ELASTICSEARCH_API_KEY") or os.getenv("ELASTIC_API_KEY")


def _cloud_id() -> str | None:
    return os.getenv("ELASTICSEARCH_CLOUD_ID") or os.getenv("ELASTIC_CLOUD_ID")


def _es_url() -> str | None:
    direct = os.getenv("ELASTICSEARCH_URL") or os.getenv("ELASTIC_URL")
    if direct:
        return direct.rstrip("/")
    cid = _cloud_id()
    if not cid or ":" not in cid:
        return None
    try:
        encoded = cid.split(":", 1)[1]
        host = base64.b64decode(encoded).decode("utf-8").split("$")[0]
        if not host.startswith("http"):
            host = f"https://{host}"
        return host.rstrip("/")
    except Exception:
        return None


def kibana_url() -> str | None:
    explicit = os.getenv("KIBANA_URL") or os.getenv("ELASTIC_KIBANA_URL")
    if explicit:
        return explicit.rstrip("/")
    cid = _cloud_id()
    if not cid or ":" not in cid:
        return None
    try:
        encoded = cid.split(":", 1)[1]
        parts = base64.b64decode(encoded).decode("utf-8").split("$")
        if len(parts) >= 3:
            host = parts[0]
            if not host.startswith("http"):
                host = f"https://{host}"
            return host.rstrip("/")
    except Exception:
        pass
    return _es_url()


def is_configured() -> bool:
    return bool(_es_url() and _api_key())


def status() -> dict[str, Any]:
    return {
        "configured": is_configured(),
        "service": _SERVICE,
        "index": _INDEX,
        "apm_url": os.getenv("ELASTIC_APM_SERVER_URL", ""),
        "kibana_url": kibana_url() or "",
        "features": {
            "logs": is_configured(),
            "apm": bool(os.getenv("ELASTIC_APM_SERVER_URL")),
            "synthetics": bool(kibana_url() and _api_key()),
        },
    }


async def ship_event(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Index a structured event into Elasticsearch."""
    base = _es_url()
    key = _api_key()
    if not base or not key:
        return {"ok": False, "error": "elastic not configured"}

    doc = {
        "@timestamp": datetime.now(timezone.utc).isoformat(),
        "event.type": event_type,
        "service.name": _SERVICE,
        "service.environment": os.getenv("ELASTIC_ENVIRONMENT", "production"),
        "data_stream.type": "logs",
        "data_stream.dataset": "opsora.mobile",
        "data_stream.namespace": "default",
        **payload,
    }

    headers = {
        "Authorization": f"ApiKey {key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(f"{base}/{_INDEX}/_doc", headers=headers, json=doc)
            if res.status_code in (200, 201):
                return {"ok": True, "id": res.json().get("_id")}
            return {"ok": False, "status": res.status_code, "body": res.text[:500]}
    except httpx.HTTPError as exc:
        return {"ok": False, "error": str(exc)}


async def ping() -> dict[str, Any]:
    """Verify Elasticsearch connectivity."""
    base = _es_url()
    key = _api_key()
    if not base or not key:
        return {"ok": False, "error": "not configured"}
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            res = await client.get(
                f"{base}/_cluster/health",
                headers={"Authorization": f"ApiKey {key}"},
            )
            if res.status_code == 200:
                data = res.json()
                return {"ok": True, "status": data.get("status"), "cluster": data.get("cluster_name")}
            return {"ok": False, "status": res.status_code}
    except httpx.HTTPError as exc:
        return {"ok": False, "error": str(exc)}
