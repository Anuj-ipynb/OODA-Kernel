import logging
import os

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from .env file automatically
load_dotenv()

def get_llm_api_key() -> str | None:
    """
    Returns the configured LLM API key.
    Checks LLM_API_KEY first, followed by provider-specific environment variables.
    Filters out default template placeholder strings and strips enclosing quotes.
    """
    raw_key = (
        os.getenv("LLM_API_KEY") or
        os.getenv("OPENROUTER_API_KEY") or
        os.getenv("NVIDIA_API_KEY") or
        os.getenv("OPENAI_API_KEY")
    )
    if not raw_key or "your_llm_api_key_here" in raw_key:
        return None
        
    clean_key = raw_key.strip(' "\'\t\n\r')
    return clean_key if clean_key else None

def get_llm_base_url() -> str:
    """
    Returns the API base URL for OpenAI-compatible endpoint.
    """
    url = os.getenv("LLM_BASE_URL")
    if url:
        return url.strip(' "\'\t\n\r')
    
    if os.getenv("OPENROUTER_API_KEY"):
        return "https://openrouter.ai/api/v1"
    elif os.getenv("NVIDIA_API_KEY"):
        return "https://integrate.api.nvidia.com/v1"
    
    return "https://api.openai.com/v1"

def get_llm_model() -> str:
    """
    Returns the target model identifier.
    """
    model = os.getenv("LLM_MODEL")
    if model and model.strip():
        return model.strip(' "\'\t\n\r')
    
    if os.getenv("OPENROUTER_API_KEY"):
        return "anthropic/claude-3.5-sonnet"
    elif os.getenv("NVIDIA_API_KEY"):
        return "meta/llama-3.1-70b-instruct"
    
    return "gpt-4o-mini"
