"""Cloud provider adapter factory."""
from __future__ import annotations

from typing import Any


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
