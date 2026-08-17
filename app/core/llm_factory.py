import os
import logging
from dotenv import load_dotenv
from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel

# Attempt to import NVIDIA Chat model; optional dependency
try:
    from langchain_nvidia_ai_endpoints import ChatNVIDIA
    _has_nvidia = True
except Exception:
    _has_nvidia = False

logger = logging.getLogger(__name__)

def get_llm() -> BaseChatModel:
    """Factory returning a configured LLM.

    Uses NVIDIA `ChatNVIDIA` when the selected model indicates an NVIDIA NIM.
    Falls back to `ChatOpenAI` for other providers.
    """
    # Reload env variables to capture any runtime changes
    load_dotenv(override=True)

    api_key = (
        os.getenv("NVIDIA_API_KEY")
        or os.getenv("LLM_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("OPENROUTER_API_KEY")
    )
    base_url = os.getenv("LLM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    model_name = os.getenv("LLM_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")

    if not api_key:
        logger.warning("No LLM API key found; using dummy placeholder.")
        api_key = "dummy_key"

    # Use NVIDIA endpoint when appropriate
    if _has_nvidia and ("nvidia" in model_name.lower() or "nemotron" in model_name.lower()):
        logger.info("Creating NVIDIA ChatNVIDIA client for model %s", model_name)
        return ChatNVIDIA(
            model=model_name,
            api_key=api_key,
            temperature=0.2,
            top_p=0.95,
            max_tokens=4096,
            reasoning_budget=16384,
            chat_template_kwargs={"enable_thinking": True},
        )

    # Fallback to OpenAI-compatible client
    from langchain_openai import ChatOpenAI

    extra_body: Optional[dict] = None
    # Example: could add extra_body for other providers if needed

    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0.2,
        max_completion_tokens=4096,
        extra_body=extra_body,
        request_timeout=30.0,
    )
