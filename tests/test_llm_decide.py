import os
import pytest
from app.core.config import get_llm_api_key, get_llm_base_url, get_llm_model
from app.agents.decide import apply_safety_policy, decide_node

def test_generic_llm_api_key_resolution(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-test-generic-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://custom-llm-provider.com/v1")
    monkeypatch.setenv("LLM_MODEL", "custom-deep-model")
    
    assert get_llm_api_key() == "sk-test-generic-key"
    assert get_llm_base_url() == "https://custom-llm-provider.com/v1"
    assert get_llm_model() == "custom-deep-model"

def test_safety_policy_override_dangerous_keyword():
    """
    Verifies that if an LLM generates a dangerous command with a low risk score (e.g. 0.20),
    the Safety Policy Guardrail forces risk_score to 0.95 and is_destructive to True.
    """
    command = "rm -rf /var/log/app_cache/*"
    llm_risk_score = 0.20
    llm_is_destructive = False
    reasoning = "Clearing log cache."
    
    final_risk, final_destructive, final_reasoning = apply_safety_policy(
        command, llm_risk_score, llm_is_destructive, reasoning
    )
    
    assert final_risk >= 0.95
    assert final_destructive is True
    assert "[SAFETY GUARDRAIL OVERRIDE]" in final_reasoning

def test_safety_policy_normal_command():
    """Normal commands should preserve the LLM's original risk score."""
    command = "echo 'remediating...'"
    llm_risk_score = 0.30
    llm_is_destructive = False
    reasoning = "Normal check."
    
    final_risk, final_destructive, final_reasoning = apply_safety_policy(
        command, llm_risk_score, llm_is_destructive, reasoning
    )
    
    assert final_risk == 0.30
    assert final_destructive is False
    assert "[SAFETY GUARDRAIL OVERRIDE]" not in final_reasoning

def test_decide_node_fallback_heuristic():
    state = {
        "root_cause_analysis": "Database connection pool saturation",
        "step_history": []
    }
    result = decide_node(state)
    assert result["status"] == "DECIDING"
    assert "proposed_command" in result
    assert result["risk_score"] > 0.70
