"""GCP Compute Engine adapter. google-cloud-compute imported lazily."""
from __future__ import annotations

from typing import Any, Optional


class GCPAdapter:
    def __init__(self, credentials_ref: Optional[str] = None, project: str = "", zone: str = "us-central1-a") -> None:
        self.credentials_ref = credentials_ref
        self.project = project
        self.zone = zone

    def _client(self) -> Any:
        try:
            from google.cloud import compute_v1
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("google-cloud-compute not installed") from exc
        return compute_v1.InstancesClient()

    def list_instances(self) -> list[dict[str, Any]]:
        client = self._client()
        resp = client.list(project=self.project, zone=self.zone)
        out: list[dict[str, Any]] = []
        for inst in resp:
            ip = next((a.nat_ip for a in (inst.network_interfaces or []) if getattr(a, "nat_ip", None)), None)
            out.append({
                "id": str(inst.id),
                "public_ip": ip,
                "state": inst.status,
                "type": getattr(inst.machine_type, "value", inst.machine_type),
                "name": inst.name,
            })
        return out

    def create_instance(self, spec: dict[str, Any]) -> dict[str, Any]:
        try:
            from google.cloud import compute_v1
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("google-cloud-compute not installed") from exc
        from google.cloud import compute_v1 as c  # noqa: F811

        disk = c.AttachedDisk(
            boot=True, auto_delete=True,
            initialize_params=c.AttachedDiskInitializeParams(image=spec["image"]),
        )
        iface = c.NetworkInterface(access_configs=[c.AccessConfig(nat_i_p="")])
        inst = c.Instance(
            name=spec["name"], machine_type=f"zones/{self.zone}/machineTypes/{spec['machine_type']}",
            disks=[disk], network_interfaces=[iface],
        )
        op = self._client().insert(project=self.project, zone=self.zone, instance_resource=inst)
        return {"id": str(op.id), "state": "provisioning"}

    def destroy_instance(self, instance_id: str) -> dict[str, Any]:
        self._client().delete(project=self.project, zone=self.zone, instance=instance_id)
        return {"id": instance_id, "state": "terminated"}
