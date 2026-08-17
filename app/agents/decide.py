import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Tuple

from langchain_core.output_parsers import PydanticOutputParser
from app.core.state import IncidentState
from app.core.llm_factory import get_llm
from app.core.schemas import DecideSchema

logger = logging.getLogger(__name__)

DANGEROUS_KEYWORDS = ["rm ", "rm -rf", "drop ", "truncate ", "delete ", "shutdown", "reboot", "pg_ctl restart", "format"]

def apply_safety_policy(command: str, llm_risk_score: float, llm_is_destructive: bool, reasoning: str) -> Tuple[float, bool, str]:
    """
    Safety Policy Guardrail: Evaluates the proposed command against dangerous keyword patterns.
    Forces high risk score if dangerous keywords are present.
    """
    cmd_lower = command.lower()
    for kw in DANGEROUS_KEYWORDS:
        if kw in cmd_lower:
            override_reasoning = f"[SAFETY GUARDRAIL OVERRIDE] Flagged dangerous keyword '{kw}'. {reasoning}"
            return max(llm_risk_score, 0.95), True, override_reasoning
            
    return llm_risk_score, llm_is_destructive, reasoning

def decide_node(state: IncidentState) -> dict:
    """
    Decide Node: Formulates structured remediation commands and computes risk score, rollback commands, & destructive action flags.
    """
    start_time = time.time()
    rca = state.get("root_cause_analysis", {})
    if isinstance(rca, dict):
        root_cause = rca.get("root_cause", "Unknown failure")
        impacted = rca.get("impacted_services", [])
    else:
        root_cause = str(rca)
        impacted = []

    parser = PydanticOutputParser(pydantic_object=DecideSchema)
    format_instructions = parser.get_format_instructions()

    system_prompt = (
        "You are an Incident Response Automation Engine.\n"
        "Based on the diagnosed root cause, generate a remediation shell command, a rollback command to restore state if remediation fails, "
        "risk score (0.0 to 1.0), and indicate if the command is destructive.\n\n"
        f"{format_instructions}"
    )

    user_prompt = f"Diagnosed Root Cause: {root_cause}\nImpacted Services: {', '.join(impacted) if isinstance(impacted, list) else impacted}"

    proposed_command = ""
    rollback_command = ""
    risk_score = 0.5
    is_destructive = False
    reasoning = ""

    try:
        lower_root = root_cause.lower()
        if "database" in lower_root or "connection pool" in lower_root or "postgres" in lower_root:
            proposed_command, rollback_command, risk_score, is_destructive = _heuristic_decide(root_cause)
            reasoning = "Heuristic decision (pre‑LLM) for high‑risk root cause."
        elif "normal" in lower_root or "unspecified" in lower_root or "trace" in lower_root:
            proposed_command, rollback_command, risk_score, is_destructive = _heuristic_decide(root_cause)
            reasoning = "Heuristic decision (pre‑LLM) for normal / low-risk trace."
        else:
            llm = get_llm()
            response = llm.invoke([
                ("system", system_prompt),
                ("user", user_prompt)
            ])

            result: DecideSchema = parser.parse(response.content)

            proposed_command = result.proposed_command
            rollback_command = getattr(result, "rollback_command", None) or f"echo 'ROLLBACK FOR: {proposed_command}'"
            risk_score = result.risk_score
            is_destructive = result.is_destructive
            reasoning = result.explanation
            logger.info(f"Decide Node LLM generated command: '{proposed_command}' (Risk: {risk_score})")
    except Exception as e:
        logger.error(f"LLM Decide generation failed: {e}. Falling back to heuristic decision.")
        proposed_command, rollback_command, risk_score, is_destructive = _heuristic_decide(root_cause)
        reasoning = "Heuristic decision fallback."

    if not rollback_command:
        rollback_command = f"echo 'ROLLBACK DEFAULT FOR: {proposed_command}'"

    # Apply Safety Policy Guardrails
    risk_score, is_destructive, reasoning = apply_safety_policy(proposed_command, risk_score, is_destructive, reasoning)

    latency_ms = round((time.time() - start_time) * 1000, 2)
    step_record = {
        "node": "decide",
        "status": "COMPLETED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "latency_ms": latency_ms,
        "details": {
            "proposed_command": proposed_command,
            "rollback_command": rollback_command,
            "risk_score": risk_score,
            "is_destructive": is_destructive,
            "explanation": reasoning
        }
    }

    return {
        "status": "DECIDING",
        "proposed_command": proposed_command,
        "rollback_command": rollback_command,
        "risk_score": risk_score,
        "is_destructive": is_destructive,
        "step_history": [step_record]
    }

def _heuristic_decide(root_cause: str) -> tuple[str, str, float, bool]:
    lower_rc = root_cause.lower()
    if "database" in lower_rc or "connection pool" in lower_rc or "postgres" in lower_rc:
        return (
            "echo 'RESTARTING POSTGRES DB CONNECTION POOL' && pg_ctl restart -m fast",
            "echo 'RESTORING PREVIOUS DB POOL CONFIG' && pg_ctl reload",
            0.85,
            True
        )
    elif "disk" in lower_rc:
        return (
            "echo 'PURGING TEMP LOGS' && rm -rf /tmp/*.log",
            "echo 'RESTORING LOG ROTATION POLICIES' && systemctl restart rsyslog",
            0.40,
            False
        )
    elif "normal" in lower_rc or "unspecified" in lower_rc or "trace" in lower_rc:
        return (
            "echo 'SYSTEM NORMAL TRACE VERIFIED'",
            "echo 'NO ROLLBACK REQUIRED'",
            0.20,
            False
        )
    else:
        return (
            "echo 'RESTARTING IMPACTED SERVICES' && systemctl restart app",
            "echo 'ROLLBACK RESTART OPERATOR' && systemctl reload app",
            0.75,
            True
        )
