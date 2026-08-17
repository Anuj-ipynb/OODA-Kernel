import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from langchain_core.output_parsers import PydanticOutputParser
from app.core.state import IncidentState
from app.core.llm_factory import get_llm
from app.core.schemas import OrientAnalysisSchema

logger = logging.getLogger(__name__)

def orient_node(state: IncidentState) -> dict:
    """
    Orient Node: Analyzes normalized telemetry data to diagnose root cause using ChatNVIDIA and Pydantic output parsing.
    """
    start_time = time.time()
    raw_logs = state.get("telemetry_logs", "")
    
    if not raw_logs or not isinstance(raw_logs, str):
        raw_logs = "No telemetry logs recorded."

    parser = PydanticOutputParser(pydantic_object=OrientAnalysisSchema)
    format_instructions = parser.get_format_instructions()

    system_prompt = (
        "You are an expert Reliability Engineer & Incident Commander.\n"
        "Analyze the provided infrastructure telemetry logs and produce a structured root cause analysis.\n\n"
        f"{format_instructions}"
    )
    
    user_prompt = f"Infrastructure Telemetry Logs:\n{raw_logs}"

    analysis_result: Dict[str, Any] = {}

    try:
        llm = get_llm()
        response = llm.invoke([
            ("system", system_prompt),
            ("user", user_prompt)
        ])
        
        result: OrientAnalysisSchema = parser.parse(response.content)
        
        analysis_result = {
            "root_cause": result.root_cause,
            "impacted_services": result.impacted_services,
            "confidence_score": result.confidence_score,
            "reasoning": result.reasoning or "Structured LLM analysis completed successfully."
        }
        logger.info(f"Orient Node LLM structured diagnosis: {result.root_cause}")

    except Exception as e:
        logger.error(f"LLM Orient analysis failed: {e}. Falling back to heuristic diagnosis.")
        analysis_result = _heuristic_orient(raw_logs)

    latency_ms = round((time.time() - start_time) * 1000, 2)
    step_record = {
        "node": "orient",
        "status": "COMPLETED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "latency_ms": latency_ms,
        "details": analysis_result
    }

    return {
        "status": "ORIENTING",
        "root_cause_analysis": analysis_result,
        "step_history": [step_record]
    }

def _heuristic_orient(raw_logs: str) -> dict:
    lower_logs = raw_logs.lower()
    if "postgres" in lower_logs or "connection pool" in lower_logs or "db" in lower_logs:
        return {
            "root_cause": "PostgreSQL database connection pool exhaustion.",
            "impacted_services": ["db-service", "api-gateway"],
            "confidence_score": 0.85,
            "reasoning": "Heuristic match for connection pool / DB error signature."
        }
    elif "disk" in lower_logs or "out of space" in lower_logs:
        return {
            "root_cause": "Host disk space exhaustion in /var/log.",
            "impacted_services": ["filesystem"],
            "confidence_score": 0.90,
            "reasoning": "Heuristic match for disk space depletion."
        }
    else:
        return {
            "root_cause": "Unspecified microservice anomaly.",
            "impacted_services": ["unknown-service"],
            "confidence_score": 0.50,
            "reasoning": "Fallback general heuristic diagnosis."
        }
