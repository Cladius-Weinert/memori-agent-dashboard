"""Models listing endpoint — dynamically checks provider API keys."""
from __future__ import annotations

import os

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


def _status(*env_vars: str) -> str:
    for v in env_vars:
        if os.getenv(v):
            return "configured"
    return "missing_key"


@router.get("/models")
async def list_models() -> dict:
    nvidia = _status("NVIDIA_API_KEY", "LLM_API_KEY")
    openai = _status("OPENAI_API_KEY")
    anthropic = _status("ANTHROPIC_API_KEY")
    groq = _status("GROQ_API_KEY")
    deepseek = _status("DEEPSEEK_API_KEY")
    dashscope = _status("DASHSCOPE_API_KEY")
    tokenhub = _status("TOKENHUB_API_KEY")
    openrouter = _status("OPENROUTER_API_KEY")
    together = _status("TOGETHER_API_KEY")
    mistral = _status("MISTRAL_API_KEY")
    google = _status("GOOGLE_API_KEY", "GEMINI_API_KEY")
    xai = _status("XAI_API_KEY")
    fireworks = _status("FIREWORKS_API_KEY")
    bedrock = "configured" if os.getenv("AWS_PROFILE") or os.getenv("AWS_ACCESS_KEY_ID") else "missing_key"
    ollama = "configured"

    nvidia_base = "https://integrate.api.nvidia.com/v1"
    models = [
        # ── NVIDIA NIM (primary) ──
        {"id": "nvidia-llama-70b", "provider": "NVIDIA", "name": "meta/llama-3.1-70b-instruct", "label": "Loop default · seimbang", "role": "executor", "status": nvidia, "base_url": nvidia_base, "context": "128K"},
        {"id": "nvidia-llama-405b", "provider": "NVIDIA", "name": "meta/llama-3.1-405b-instruct", "label": "Kualitas tertinggi", "role": "executor", "status": nvidia, "base_url": nvidia_base, "context": "128K"},
        {"id": "nvidia-llama-8b", "provider": "NVIDIA", "name": "meta/llama-3.1-8b-instruct", "label": "Cepat & hemat", "role": "executor", "status": nvidia, "base_url": nvidia_base, "context": "128K"},
        {"id": "nvidia-llama-nemotron-70b", "provider": "NVIDIA", "name": "nvidia/llama-3.1-nemotron-70b-instruct", "label": "Nemotron instruct", "role": "executor", "status": nvidia, "base_url": nvidia_base, "context": "128K"},
        {"id": "nvidia-nemotron-orch", "provider": "NVIDIA", "name": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning", "label": "Orchestrator / reasoning", "role": "orchestrator", "status": nvidia, "base_url": nvidia_base, "context": "128K"},
        {"id": "nvidia-llama-vision", "provider": "NVIDIA", "name": "meta/llama-3.2-90b-vision-instruct", "label": "Vision & UI", "role": "visual", "status": nvidia, "base_url": nvidia_base, "context": "128K"},
        {"id": "nvidia-llama-11b-vision", "provider": "NVIDIA", "name": "meta/llama-3.2-11b-vision-instruct", "label": "Vision cepat", "role": "visual", "status": nvidia, "base_url": nvidia_base, "context": "128K"},
        {"id": "nvidia-deepseek-v4", "provider": "NVIDIA", "name": "deepseek-ai/deepseek-v4-pro", "label": "Deep reasoning", "role": "deep", "status": nvidia, "base_url": nvidia_base, "context": "128K"},
        {"id": "nvidia-deepseek-r1", "provider": "NVIDIA", "name": "deepseek-ai/deepseek-r1", "label": "DeepSeek R1", "role": "deep", "status": nvidia, "base_url": nvidia_base, "context": "128K"},
        {"id": "nvidia-mistral-nemo", "provider": "NVIDIA", "name": "mistralai/mistral-nemotron", "label": "Mistral via NIM", "role": "executor", "status": nvidia, "base_url": nvidia_base, "context": "128K"},
        {"id": "nvidia-mixtral", "provider": "NVIDIA", "name": "mistralai/mixtral-8x22b-instruct-v0.1", "label": "Mixtral 8x22B", "role": "executor", "status": nvidia, "base_url": nvidia_base, "context": "64K"},
        {"id": "nvidia-qwen", "provider": "NVIDIA", "name": "qwen/qwen2.5-72b-instruct", "label": "Qwen 2.5 72B", "role": "executor", "status": nvidia, "base_url": nvidia_base, "context": "128K"},
        {"id": "nvidia-gemma", "provider": "NVIDIA", "name": "google/gemma-2-27b-it", "label": "Gemma 2 27B", "role": "executor", "status": nvidia, "base_url": nvidia_base, "context": "8K"},
        {"id": "nvidia-phi", "provider": "NVIDIA", "name": "microsoft/phi-3.5-moe-instruct", "label": "Phi-3.5 MoE", "role": "executor", "status": nvidia, "base_url": nvidia_base, "context": "128K"},

        # ── OpenAI ──
        {"id": "openai-gpt4o", "provider": "OpenAI", "name": "gpt-4o", "label": "GPT-4o", "role": "executor", "status": openai, "base_url": "https://api.openai.com/v1", "context": "128K"},
        {"id": "openai-gpt4o-mini", "provider": "OpenAI", "name": "gpt-4o-mini", "label": "GPT-4o mini", "role": "executor", "status": openai, "base_url": "https://api.openai.com/v1", "context": "128K"},
        {"id": "openai-o3-mini", "provider": "OpenAI", "name": "o3-mini", "label": "o3-mini reasoning", "role": "deep", "status": openai, "base_url": "https://api.openai.com/v1", "context": "200K"},
        {"id": "openai-gpt41", "provider": "OpenAI", "name": "gpt-4.1", "label": "GPT-4.1", "role": "executor", "status": openai, "base_url": "https://api.openai.com/v1", "context": "1M"},

        # ── Anthropic ──
        {"id": "anthropic-sonnet", "provider": "Anthropic", "name": "claude-sonnet-4-20250514", "label": "Claude Sonnet 4", "role": "executor", "status": anthropic, "base_url": "https://api.anthropic.com/v1", "context": "200K"},
        {"id": "anthropic-haiku", "provider": "Anthropic", "name": "claude-3-5-haiku-latest", "label": "Claude Haiku", "role": "executor", "status": anthropic, "base_url": "https://api.anthropic.com/v1", "context": "200K"},
        {"id": "anthropic-opus", "provider": "Anthropic", "name": "claude-opus-4-20250514", "label": "Claude Opus 4", "role": "deep", "status": anthropic, "base_url": "https://api.anthropic.com/v1", "context": "200K"},

        # ── Groq ──
        {"id": "groq-llama-70b", "provider": "Groq", "name": "llama-3.3-70b-versatile", "label": "Llama 3.3 70B (cepat)", "role": "executor", "status": groq, "base_url": "https://api.groq.com/openai/v1", "context": "128K"},
        {"id": "groq-llama-8b", "provider": "Groq", "name": "llama-3.1-8b-instant", "label": "Llama 8B instant", "role": "executor", "status": groq, "base_url": "https://api.groq.com/openai/v1", "context": "128K"},
        {"id": "groq-mixtral", "provider": "Groq", "name": "mixtral-8x7b-32768", "label": "Mixtral 8x7B", "role": "executor", "status": groq, "base_url": "https://api.groq.com/openai/v1", "context": "32K"},
        {"id": "groq-qwen", "provider": "Groq", "name": "qwen/qwen3-32b", "label": "Qwen3 32B", "role": "executor", "status": groq, "base_url": "https://api.groq.com/openai/v1", "context": "128K"},

        # ── DeepSeek direct ──
        {"id": "deepseek-chat", "provider": "DeepSeek", "name": "deepseek-chat", "label": "DeepSeek Chat V3", "role": "executor", "status": deepseek, "base_url": "https://api.deepseek.com/v1", "context": "128K"},
        {"id": "deepseek-reasoner", "provider": "DeepSeek", "name": "deepseek-reasoner", "label": "DeepSeek Reasoner", "role": "deep", "status": deepseek, "base_url": "https://api.deepseek.com/v1", "context": "128K"},

        # ── Google Gemini ──
        {"id": "gemini-2flash", "provider": "Google", "name": "gemini-2.0-flash", "label": "Gemini 2.0 Flash", "role": "executor", "status": google, "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "context": "1M"},
        {"id": "gemini-25pro", "provider": "Google", "name": "gemini-2.5-pro", "label": "Gemini 2.5 Pro", "role": "deep", "status": google, "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "context": "1M"},

        # ── xAI ──
        {"id": "xai-grok", "provider": "xAI", "name": "grok-3", "label": "Grok 3", "role": "executor", "status": xai, "base_url": "https://api.x.ai/v1", "context": "128K"},
        {"id": "xai-grok-mini", "provider": "xAI", "name": "grok-3-mini", "label": "Grok 3 Mini", "role": "executor", "status": xai, "base_url": "https://api.x.ai/v1", "context": "128K"},

        # ── Mistral ──
        {"id": "mistral-large", "provider": "Mistral", "name": "mistral-large-latest", "label": "Mistral Large", "role": "executor", "status": mistral, "base_url": "https://api.mistral.ai/v1", "context": "128K"},
        {"id": "mistral-small", "provider": "Mistral", "name": "mistral-small-latest", "label": "Mistral Small", "role": "executor", "status": mistral, "base_url": "https://api.mistral.ai/v1", "context": "32K"},

        # ── OpenRouter / Together / Fireworks (meta-routers) ──
        {"id": "openrouter-auto", "provider": "OpenRouter", "name": "openrouter/auto", "label": "Auto-route", "role": "executor", "status": openrouter, "base_url": "https://openrouter.ai/api/v1", "context": "Dynamic"},
        {"id": "together-llama70", "provider": "Together", "name": "meta-llama/Llama-3.3-70B-Instruct-Turbo", "label": "Llama 3.3 70B Turbo", "role": "executor", "status": together, "base_url": "https://api.together.xyz/v1", "context": "128K"},
        {"id": "fireworks-llama70", "provider": "Fireworks", "name": "accounts/fireworks/models/llama-v3p3-70b-instruct", "label": "Llama 3.3 70B", "role": "executor", "status": fireworks, "base_url": "https://api.fireworks.ai/inference/v1", "context": "128K"},

        # ── Alibaba / Tencent ──
        {"id": "alibaba-qwen-plus", "provider": "Alibaba/DashScope", "name": "qwen-plus", "label": "Qwen Plus", "role": "executor", "status": dashscope, "base_url": os.getenv("ALIBABA_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"), "context": "128K"},
        {"id": "alibaba-qwen-turbo", "provider": "Alibaba/DashScope", "name": "qwen-turbo", "label": "Qwen Turbo", "role": "executor", "status": dashscope, "base_url": os.getenv("ALIBABA_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"), "context": "8K"},
        {"id": "alibaba-qwen-max", "provider": "Alibaba/DashScope", "name": "qwen-max", "label": "Qwen Max", "role": "deep", "status": dashscope, "base_url": os.getenv("ALIBABA_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"), "context": "32K"},
        {"id": "tokenhub-deepseek", "provider": "Tencent TokenHub", "name": "deepseek-v3", "label": "DeepSeek V3", "role": "executor", "status": tokenhub, "base_url": "https://tokenhub.tencentmaas.com/v1", "context": "128K"},
        {"id": "tokenhub-hunyuan", "provider": "Tencent TokenHub", "name": "hunyuan-standard", "label": "Hunyuan", "role": "executor", "status": tokenhub, "base_url": "https://tokenhub.tencentmaas.com/v1", "context": "32K"},

        # ── AWS / Local ──
        {"id": "bedrock-claude", "provider": "AWS Bedrock", "name": "anthropic.claude-3-5-sonnet-20241022-v2:0", "label": "Claude 3.5 Sonnet", "role": "executor", "status": bedrock, "base_url": "https://bedrock-runtime.us-east-1.amazonaws.com", "context": "200K"},
        {"id": "local-ollama-llama", "provider": "Local/Ollama", "name": "llama3.1", "label": "Ollama Llama 3.1", "role": "executor", "status": ollama, "base_url": "http://localhost:11434/v1", "context": "Dynamic"},
        {"id": "local-ollama-qwen", "provider": "Local/Ollama", "name": "qwen2.5", "label": "Ollama Qwen 2.5", "role": "executor", "status": ollama, "base_url": "http://localhost:11434/v1", "context": "Dynamic"},
        {"id": "local-ollama-mistral", "provider": "Local/Ollama", "name": "mistral", "label": "Ollama Mistral", "role": "executor", "status": ollama, "base_url": "http://localhost:11434/v1", "context": "Dynamic"},
    ]

    configured = [m for m in models if m["status"] == "configured"]
    return {
        "models": models,
        "total": len(models),
        "configured": len(configured),
        "default": settings.LLM_MODEL or "meta/llama-3.1-70b-instruct",
        "providers": sorted({m["provider"] for m in models}),
    }
