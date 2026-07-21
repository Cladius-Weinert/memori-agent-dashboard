"""Vultr instance adapter. Uses httpx against https://api.vultr.com/v2/."""
from __future__ import annotations

import os
from typing import Any, Optional

import httpx


class VultrAdapter:
    BASE = "https://api.vultr.com/v2"

    def __init__(self, credentials_ref: Optional[str] = None, api_key: str = "") -> None:
        self.credentials_ref = credentials_ref
        # if api_key not given, try env var named in credentials_ref
        self.api_key = api_key or (os.environ.get(credentials_ref) if credentials_ref else os.environ.get("VULTR_API_KEY", ""))

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def list_instances(self) -> list[dict[str, Any]]:
        r = httpx.get(f"{self.BASE}/instances", headers=self._headers(), timeout=30.0)
        r.raise_for_status()
        out: list[dict[str, Any]] = []
        for inst in r.json().get("instances", []):
            out.append({
                "id": inst["id"],
                "public_ip": inst.get("main_ip"),
                "state": inst.get("status"),
                "type": inst.get("plan"),
                "name": inst.get("label"),
            })
        return out

    def create_instance(self, spec: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "region": spec.get("region", "ewr"),
            "plan": spec.get("plan", "vc2-1c-1gb"),
            "os_id": spec.get("os_id", 1742),  # Ubuntu 22.04 x64
            "label": spec.get("name", "memori-instance"),
            "ssh_key_id": spec.get("ssh_key_id"),
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        r = httpx.post(f"{self.BASE}/instances", json=payload, headers=self._headers(), timeout=30.0)
        r.raise_for_status()
        data = r.json().get("instance", {})
        return {"id": data.get("id"), "public_ip": data.get("main_ip"), "state": data.get("status")}

    def destroy_instance(self, instance_id: str) -> dict[str, Any]:
        r = httpx.delete(f"{self.BASE}/instances/{instance_id}", headers=self._headers(), timeout=30.0)
        r.raise_for_status()
        return {"id": instance_id, "state": "destroyed"}


_ADAPTERS = {
    "aws": "app.services.providers.aws.AWSAdapter",
    "gcp": "app.services.providers.gcp.GCPAdapter",
    "digitalocean": "app.services.providers.digitalocean.DigitalOceanAdapter",
    "vultr": "app.services.providers.vultr.VultrAdapter",
}


def get_adapter(provider_type: str, **kwargs: Any) -> Any:
    """Instantiate adapter by provider type string."""
    if provider_type == "aws":
        from app.services.providers.aws import AWSAdapter
        return AWSAdapter(**kwargs)
    if provider_type == "gcp":
        from app.services.providers.gcp import GCPAdapter
        return GCPAdapter(**kwargs)
    if provider_type == "digitalocean":
        from app.services.providers.digitalocean import DigitalOceanAdapter
        return DigitalOceanAdapter(**kwargs)
    if provider_type == "vultr":
        from app.services.providers.vultr import VultrAdapter
        return VultrAdapter(**kwargs)
    raise ValueError(f"unknown provider type: {provider_type}")
