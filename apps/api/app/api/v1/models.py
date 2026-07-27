"""Models listing endpoint — dynamically checks provider API keys."""
from __future__ import annotations

import os

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


def _key(env_var: str) -> str:
    return "configured" if os.getenv(env_var) else "missing_key"


@router.get("/models")
async def list_models() -> dict:
    nvidia_status = _key("NVIDIA_API_KEY")
    dashscope_status = _key("DASHSCOPE_API_KEY")
    tokenhub_status = _key("TOKENHUB_API_KEY")
    bedrock_status = "configured" if os.getenv("AWS_PROFILE") or os.getenv("AWS_ACCESS_KEY_ID") else "missing_key"
    ollama_status = "configured"

    models = [
        {"id": "nvidia-llama", "provider": "NVIDIA", "name": "meta/llama-3.1-70b-instruct", "label": "Best balance", "status": nvidia_status, "base_url": "https://integrate.api.nvidia.com/v1", "context": "128K"},
        {"id": "nvidia-nemotron", "provider": "NVIDIA", "name": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning", "label": "Orchestrator", "status": nvidia_status, "base_url": "https://integrate.api.nvidia.com/v1", "context": "128K"},
        {"id": "nvidia-llama-vision", "provider": "NVIDIA", "name": "meta/llama-3.2-90b-vision-instruct", "label": "Vision & UI", "status": nvidia_status, "base_url": "https://integrate.api.nvidia.com/v1", "context": "128K"},
        {"id": "nvidia-deepseek", "provider": "NVIDIA", "name": "deepseek-ai/deepseek-v4-pro", "label": "Deep reasoning", "status": nvidia_status, "base_url": "https://integrate.api.nvidia.com/v1", "context": "128K"},
        {"id": "alibaba-qwen-plus", "provider": "Alibaba/DashScope", "name": "qwen-plus", "label": "Production (Alibaba)", "status": dashscope_status, "base_url": os.getenv("ALIBABA_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"), "context": "128K"},
        {"id": "alibaba-qwen-turbo", "provider": "Alibaba/DashScope", "name": "qwen-turbo", "label": "Fast (Alibaba)", "status": dashscope_status, "base_url": os.getenv("ALIBABA_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"), "context": "8K"},
        {"id": "alibaba-qwen-max", "provider": "Alibaba/DashScope", "name": "qwen-max", "label": "Max quality", "status": dashscope_status, "base_url": os.getenv("ALIBABA_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"), "context": "32K"},
        {"id": "tokenhub-deepseek", "provider": "Tencent TokenHub", "name": "deepseek-v3", "label": "Fast reasoning", "status": tokenhub_status, "base_url": "https://tokenhub.tencentmaas.com/v1", "context": "128K"},
        {"id": "tokenhub-hunyuan", "provider": "Tencent TokenHub", "name": "hunyuan-standard", "label": "Hunyuan", "status": tokenhub_status, "base_url": "https://tokenhub.tencentmaas.com/v1", "context": "32K"},
        {"id": "bedrock-claude", "provider": "AWS Bedrock", "name": "anthropic.claude-3-sonnet", "label": "Production (AWS)", "status": bedrock_status, "base_url": "https://bedrock-runtime.us-east-1.amazonaws.com", "context": "200K"},
        {"id": "local-ollama", "provider": "Local/Ollama", "name": "llama3.1", "label": "Free private", "status": ollama_status, "base_url": "http://localhost:11434", "context": "Dynamic"},
    ]
    return {"models": models, "total": len(models), "default": settings.LLM_MODEL or "meta/llama-3.1-70b-instruct"}
