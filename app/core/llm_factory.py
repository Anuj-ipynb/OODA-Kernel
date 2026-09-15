import logging
import os
from typing import Any

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult

logger = logging.getLogger(__name__)

# Attempt to import ChatNVIDIA (optional dependency)
try:
    from langchain_nvidia_ai_endpoints import ChatNVIDIA
    _has_nvidia = True
except ImportError:
    _has_nvidia = False

from pydantic import ConfigDict


class ResilientLLMWrapper(BaseChatModel):
    """
    Resilient LLM Wrapper that provides multi-tier fallback mechanism:
    1. Primary Model (NVIDIA NIM or OpenAI / OpenRouter)
    2. Local Ollama Model (http://localhost:11434/v1)
    3. Graceful exception for heuristic fallback handling
    """
    primary_llm: BaseChatModel
    fallback_llm: BaseChatModel | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def _llm_type(self) -> str:
        return "resilient_wrapper"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        # Try primary LLM
        try:
            return self.primary_llm._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
        except Exception as primary_err:
            logger.warning(f"[LLM WRAPPER] Primary LLM execution failed: {primary_err}")
            
            # Try Ollama fallback if available
            if self.fallback_llm is not None:
                try:
                    logger.info("[LLM WRAPPER] Falling back to local Ollama model...")
                    return self.fallback_llm._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
                except Exception as fallback_err:  # noqa: BLE001
                    logger.warning(f"[LLM WRAPPER] Ollama fallback execution failed: {fallback_err}")

            raise

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        try:
            return await self.primary_llm._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)
        except Exception as primary_err:
            logger.warning(f"[LLM WRAPPER] Async Primary LLM execution failed: {primary_err}")
            if self.fallback_llm is not None:
                try:
                    logger.info("[LLM WRAPPER] Falling back to local Ollama model (async)...")
                    return await self.fallback_llm._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)
                except Exception as fallback_err:  # noqa: BLE001
                    logger.warning(f"[LLM WRAPPER] Async Ollama fallback execution failed: {fallback_err}")
            raise


def _build_ollama_fallback(timeout: float) -> BaseChatModel | None:
    """Instantiates a local Ollama OpenAI-compatible Chat client if configured or available."""
    from langchain_openai import ChatOpenAI

    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
    
    try:
        return ChatOpenAI(
            model=ollama_model,
            api_key="ollama",
            base_url=ollama_base_url,
            temperature=0.2,
            max_completion_tokens=2048,
            request_timeout=timeout,
        )
    except Exception as e:  # noqa: BLE001
        logger.debug(f"Could not build Ollama fallback: {e}")
        return None


def get_llm(force_timeout: float | None = None) -> BaseChatModel:
    """Factory returning a configured resilient LLM wrapper.
    
    Features:
    - Automatically detects test environment (`PYTEST_CURRENT_TEST` or `OODA_TEST_MODE`) and sets tight 2.0s timeout to avoid 3-minute test delays.
    - Provider hierarchy: NVIDIA NIM -> OpenAI/OpenRouter -> Local Ollama Fallback.
    """
    load_dotenv(override=True)

    is_test = bool(os.getenv("PYTEST_CURRENT_TEST") or os.getenv("OODA_TEST_MODE"))
    timeout = force_timeout or (2.0 if is_test else 30.0)

    api_key = (
        os.getenv("NVIDIA_API_KEY")
        or os.getenv("LLM_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("OPENROUTER_API_KEY")
    )
    base_url = os.getenv("LLM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    model_name = os.getenv("LLM_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")

    if not api_key:
        logger.info("No LLM API key configured; using default fallback settings.")
        api_key = "dummy_key"

    primary_llm: BaseChatModel

    if _has_nvidia and ("nvidia" in model_name.lower() or "nemotron" in model_name.lower()):
        logger.info("Creating ChatNVIDIA client for model %s (timeout: %.1fs)", model_name, timeout)
        primary_llm = ChatNVIDIA(
            model=model_name,
            api_key=api_key,
            temperature=0.2,
            top_p=0.95,
            max_completion_tokens=2048,
            timeout=int(timeout),
        )
    else:
        from langchain_openai import ChatOpenAI
        logger.info("Creating ChatOpenAI client for model %s at %s (timeout: %.1fs)", model_name, base_url, timeout)
        primary_llm = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=0.2,
            max_completion_tokens=4096,
            request_timeout=timeout,
        )

    ollama_fallback = _build_ollama_fallback(timeout=timeout)
    return ResilientLLMWrapper(primary_llm=primary_llm, fallback_llm=ollama_fallback)
