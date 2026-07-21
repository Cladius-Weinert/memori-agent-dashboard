"""AWS EC2 provider adapter. boto3 imported lazily."""
from __future__ import annotations

from typing import Any, Optional


class AWSAdapter:
    def __init__(self, credentials_ref: Optional[str] = None, region: str = "us-east-1") -> None:
        self.credentials_ref = credentials_ref
        self.region = region

    def _client(self) -> Any:
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("boto3 not installed") from exc
        return boto3.client("ec2", region_name=self.region)

    def list_instances(self) -> list[dict[str, Any]]:
        client = self._client()
        resp = client.describe_instances()
        out: list[dict[str, Any]] = []
        for res in resp.get("Reservations", []):
            for inst in res.get("Instances", []):
                out.append({
                    "id": inst["InstanceId"],
                    "public_ip": inst.get("PublicIpAddress"),
                    "state": inst.get("State", {}).get("Name", "unknown"),
                    "type": inst.get("InstanceType"),
                    "name": next(
                        (t["Value"] for t in inst.get("Tags", []) if t.get("Key") == "Name"),
                        inst["InstanceId"],
                    ),
                })
        return out

    def create_instance(self, spec: dict[str, Any]) -> dict[str, Any]:
        client = self._client()
        resp = client.run_instances(
            ImageId=spec["ami"],
            InstanceType=spec["instance_type"],
            MinCount=1,
            MaxCount=1,
            KeyName=spec.get("key_name"),
            TagSpecifications=[{
                "ResourceType": "instance",
                "Tags": [{"Key": "Name", "Value": spec.get("name", "memori-instance")}],
            }],
        )
        inst = resp["Instances"][0]
        return {"id": inst["InstanceId"], "public_ip": None, "state": inst["State"]["Name"]}

    def destroy_instance(self, instance_id: str) -> dict[str, Any]:
        client = self._client()
        client.terminate_instances(InstanceIds=[instance_id])
        return {"id": instance_id, "state": "terminated"}
