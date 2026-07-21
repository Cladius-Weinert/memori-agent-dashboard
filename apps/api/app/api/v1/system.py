"""System health endpoint — local server metrics."""
from __future__ import annotations

import os
import socket
import subprocess
import time

import psutil
from fastapi import APIRouter

router = APIRouter()

_BOOT_TIME = psutil.boot_time()

_SERVICES = {
    "opsora-proxy": ("127.0.0.1", 8090),
    "redis": ("127.0.0.1", 6379),
    "ollama": ("127.0.0.1", 11434),
    "open-webui": ("127.0.0.1", 8080),
}

_DOCKER_SOCKET = "/var/run/docker.sock"


def _port_open(host: str, port: int, timeout: float = 0.3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _docker_running() -> bool:
    return os.path.exists(_DOCKER_SOCKET)


def _docker_container_count() -> int:
    if not _docker_running():
        return 0
    try:
        out = subprocess.check_output(
            ["docker", "ps", "-q"], stderr=subprocess.DEVNULL, timeout=3
        )
        return len(out.strip().splitlines()) if out.strip() else 0
    except Exception:
        return -1  # unknown


def _gather_health() -> dict:
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    services: dict[str, bool] = {}
    for name, (host, port) in _SERVICES.items():
        services[name] = _port_open(host, port)

    return {
        "hostname": socket.gethostname(),
        "uptime_seconds": round(time.time() - _BOOT_TIME, 1),
        "cpu_percent": psutil.cpu_percent(interval=0),
        "cpu_count": psutil.cpu_count(),
        "memory_total_mb": round(mem.total / 1024 / 1024, 1),
        "memory_used_mb": round(mem.used / 1024 / 1024, 1),
        "memory_percent": mem.percent,
        "disk_total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
        "disk_used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
        "disk_percent": disk.percent,
        "docker_running": _docker_running(),
        "docker_containers": _docker_container_count(),
        "services": services,
        "timestamp": time.time(),
    }


@router.get("/health")
async def health() -> dict:
    """Return local server health metrics. No auth required."""
    try:
        return _gather_health()
    except Exception as exc:
        return {"error": str(exc), "timestamp": time.time()}
