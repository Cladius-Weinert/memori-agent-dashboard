"""DigitalOcean droplet adapter. python-digitalocean imported lazily."""
from __future__ import annotations

from typing import Any, Optional


class DigitalOceanAdapter:
    def __init__(self, credentials_ref: Optional[str] = None, token: str = "") -> None:
        self.credentials_ref = credentials_ref
        self.token = token

    def _manager(self) -> Any:
        try:
            from digitalocean import Manager
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("python-digitalocean not installed") from exc
        return Manager(token=self.token)

    def list_instances(self) -> list[dict[str, Any]]:
        mgr = self._manager()
        out: list[dict[str, Any]] = []
        for d in mgr.get_all_droplets():
            out.append({
                "id": str(d.id),
                "public_ip": d.ip_address,
                "state": d.status,
                "type": d.size_slug,
                "name": d.name,
            })
        return out

    def create_instance(self, spec: dict[str, Any]) -> dict[str, Any]:
        try:
            from digitalocean import Droplet
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("python-digitalocean not installed") from exc
        d = Droplet(
            token=self.token, name=spec["name"], region=spec.get("region", "nyc3"),
            image=spec.get("image", "ubuntu-22-04-x64"), size_slug=spec.get("size", "s-1vcpu-1gb"),
            ssh_keys=spec.get("ssh_keys", []),
        ).create()
        return {"id": str(d.id), "public_ip": None, "state": "new"}

    def destroy_instance(self, instance_id: str) -> dict[str, Any]:
        mgr = self._manager()
        d = mgr.get_droplet(int(instance_id))
        d.destroy()
        return {"id": instance_id, "state": "destroyed"}
