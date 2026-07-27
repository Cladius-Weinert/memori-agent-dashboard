"""Per-user encrypted storage for LLM providers and custom MCP servers."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

CONFIG_ROOT = Path(os.getenv("OPSORA_CONFIG_DIR", "/home/ubuntu/.opsora/users"))

PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "nvidia": {"label": "NVIDIA NIM", "base_url": "https://integrate.api.nvidia.com/v1"},
    "openai": {"label": "OpenAI", "base_url": "https://api.openai.com/v1"},
    "anthropic": {"label": "Anthropic", "base_url": "https://api.anthropic.com/v1"},
    "dashscope": {"label": "DashScope", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    "groq": {"label": "Groq", "base_url": "https://api.groq.com/openai/v1"},
    "deepseek": {"label": "DeepSeek", "base_url": "https://api.deepseek.com/v1"},
    "custom": {"label": "Custom", "base_url": ""},
}


def _fernet() -> Fernet:
    secret = settings.JWT_SECRET or "opsora-dev-secret-change-me"
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


def _user_dir(user_id: int) -> Path:
    d = CONFIG_ROOT / str(user_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _read_json(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _write_json(path: Path, data: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken:
        return ""


def _mask_key(key: str) -> str:
    if len(key) <= 8:
        return "••••"
    return f"{key[:4]}…{key[-4:]}"


# ── LLM Providers ──────────────────────────────────────────────

def list_providers(user_id: int, *, reveal: bool = False) -> list[dict[str, Any]]:
    rows = _read_json(_user_dir(user_id) / "providers.json")
    out: list[dict[str, Any]] = []
    for r in rows:
        api_key = _decrypt(r.get("api_key_enc", "")) if reveal else ""
        item = {
            "id": r["id"],
            "name": r.get("name", ""),
            "preset": r.get("preset", "custom"),
            "base_url": r.get("base_url", ""),
            "default_model": r.get("default_model", ""),
            "enabled": r.get("enabled", True),
            "api_key_masked": _mask_key(api_key) if api_key else r.get("api_key_masked", ""),
        }
        if reveal:
            item["api_key"] = api_key
        out.append(item)
    return out


def upsert_provider(user_id: int, data: dict[str, Any]) -> dict[str, Any]:
    path = _user_dir(user_id) / "providers.json"
    rows = _read_json(path)
    pid = data.get("id") or f"p_{len(rows) + 1}_{hashlib.md5(data.get('name', '').encode()).hexdigest()[:6]}"
    preset = data.get("preset", "custom")
    preset_info = PROVIDER_PRESETS.get(preset, PROVIDER_PRESETS["custom"])
    entry = {
        "id": pid,
        "name": data.get("name") or preset_info["label"],
        "preset": preset,
        "base_url": data.get("base_url") or preset_info["base_url"],
        "default_model": data.get("default_model", ""),
        "enabled": data.get("enabled", True),
    }
    if data.get("api_key"):
        entry["api_key_enc"] = _encrypt(data["api_key"])
        entry["api_key_masked"] = _mask_key(data["api_key"])
    else:
        old = next((r for r in rows if r["id"] == pid), None)
        if old:
            entry["api_key_enc"] = old.get("api_key_enc", "")
            entry["api_key_masked"] = old.get("api_key_masked", "")

    rows = [r for r in rows if r.get("id") != pid]
    rows.append(entry)
    _write_json(path, rows)
    return list_providers(user_id)[-1]


def delete_provider(user_id: int, provider_id: str) -> bool:
    path = _user_dir(user_id) / "providers.json"
    rows = _read_json(path)
    new_rows = [r for r in rows if r.get("id") != provider_id]
    if len(new_rows) == len(rows):
        return False
    _write_json(path, new_rows)
    return True


def get_provider_client(user_id: int, provider_id: str | None = None) -> dict[str, str] | None:
    """Return api_key + base_url for first enabled provider or by id."""
    for p in list_providers(user_id, reveal=True):
        if not p.get("enabled"):
            continue
        if provider_id and p["id"] != provider_id:
            continue
        key = p.get("api_key", "")
        if key and p.get("base_url"):
            return {"api_key": key, "base_url": p["base_url"], "model": p.get("default_model", "")}
    return None


# ── MCP Servers ────────────────────────────────────────────────

def list_mcp_servers(user_id: int) -> list[dict[str, Any]]:
    return _read_json(_user_dir(user_id) / "mcp_servers.json")


def upsert_mcp_server(user_id: int, data: dict[str, Any]) -> dict[str, Any]:
    path = _user_dir(user_id) / "mcp_servers.json"
    rows = _read_json(path)
    sid = data.get("id") or f"mcp_{len(rows) + 1}_{hashlib.md5(data.get('name', '').encode()).hexdigest()[:6]}"
    entry: dict[str, Any] = {
        "id": sid,
        "name": data.get("name", "custom-mcp"),
        "transport": data.get("transport", "http"),
        "url": data.get("url", ""),
        "description": data.get("description", ""),
        "enabled": data.get("enabled", True),
        "custom": True,
    }
    if data.get("auth_token"):
        entry["auth_token_enc"] = _encrypt(data["auth_token"])
    else:
        old = next((r for r in rows if r.get("id") == sid), None)
        if old and old.get("auth_token_enc"):
            entry["auth_token_enc"] = old["auth_token_enc"]

    rows = [r for r in rows if r.get("id") != sid]
    rows.append(entry)
    _write_json(path, rows)
    return {k: v for k, v in entry.items() if not k.endswith("_enc")}


def delete_mcp_server(user_id: int, server_id: str) -> bool:
    path = _user_dir(user_id) / "mcp_servers.json"
    rows = _read_json(path)
    new_rows = [r for r in rows if r.get("id") != server_id]
    if len(new_rows) == len(rows):
        return False
    _write_json(path, new_rows)
    return True


def get_mcp_auth(user_id: int, server_id: str) -> str:
    for s in _read_json(_user_dir(user_id) / "mcp_servers.json"):
        if s.get("id") == server_id and s.get("auth_token_enc"):
            return _decrypt(s["auth_token_enc"])
    return ""
