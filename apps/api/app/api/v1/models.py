"""Models listing endpoint — dynamically checks provider API keys."""
from __future__ import annotations

import os

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


def _key(*env_vars: str) -> str:
    for env_var in env_vars:
        if os.getenv(env_var):
            return "configured"
    return "missing_key"


@router.get("/models")
async def list_models() -> dict:
    nvidia_status = _key("LLM_API_KEY", "NVIDIA_API_KEY", "NGC_CLI_API_KEY")
    dashscope_status = _key("DASHSCOPE_API_KEY")
    tokenhub_status = _key("TOKENHUB_API_KEY")
    bedrock_status = "configured" if os.getenv("AWS_PROFILE") or os.getenv("AWS_ACCESS_KEY_ID") else "missing_key"
    ollama_status = "configured"

    models = [
        {"id": "nvidia-llama", "provider": "NVIDIA", "name": "Llama-3.1-70B", "label": "Best balance", "status": nvidia_status, "base_url": settings.LLM_BASE_URL, "context": "128K"},
        {"id": "nvidia-mistral-nemo", "provider": "NVIDIA", "name": "Mistral NeMo", "label": "Fast GPU", "status": nvidia_status, "base_url": settings.LLM_BASE_URL, "context": "128K"},
        {"id": "nvidia-qwen3-80b", "provider": "NVIDIA NVCF", "name": "Qwen3-Next-80B", "label": "High quality (NVCF)", "status": nvidia_status, "base_url": "https://api.nvcf.nvidia.com/v2/nvcf", "context": "128K"},
        {"id": "alibaba-qwen", "provider": "Alibaba/DashScope", "name": "Qwen2.5-72B", "label": "Large context", "status": dashscope_status, "base_url": os.getenv("ALIBABA_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"), "context": "32K"},
        {"id": "alibaba-qwen-plus", "provider": "Alibaba/DashScope", "name": "qwen-plus", "label": "Production (Alibaba)", "status": dashscope_status, "base_url": os.getenv("ALIBABA_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"), "context": "128K"},
        {"id": "alibaba-qwen-turbo", "provider": "Alibaba/DashScope", "name": "qwen-turbo", "label": "Fast (Alibaba)", "status": dashscope_status, "base_url": os.getenv("ALIBABA_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"), "context": "8K"},
        {"id": "tokenhub-deepseek", "provider": "TokenHub/Tencent", "name": "DeepSeek-V3", "label": "Fast reasoning", "status": tokenhub_status, "base_url": "https://open.toscloud.com/v1", "context": "128K"},
        {"id": "tokenhub-deepseek-r1", "provider": "TokenHub/Tencent", "name": "DeepSeek-R1", "label": "Reasoning", "status": tokenhub_status, "base_url": "https://open.toscloud.com/v1", "context": "64K"},
        {"id": "tokenhub-doubao", "provider": "TokenHub/Tencent", "name": "Doubao-Pro-32k", "label": "ByteDance", "status": tokenhub_status, "base_url": "https://open.toscloud.com/v1", "context": "32K"},
        {"id": "bedrock-claude", "provider": "AWS Bedrock", "name": "Claude Sonnet", "label": "Production (AWS)", "status": bedrock_status, "base_url": "https://bedrock-runtime.us-east-1.amazonaws.com", "context": "200K"},
        {"id": "local-ollama", "provider": "Local/Ollama", "name": "Ollama", "label": "Free private", "status": ollama_status, "base_url": "http://localhost:11434", "context": "Dynamic"},
    ]
    return {"models": models, "total": len(models), "default": settings.LLM_MODEL or "meta/llama-3.1-70b-instruct"}
