import subprocess
import shutil
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def is_docker_available() -> bool:
    """Check if Docker CLI is available on host PATH."""
    return shutil.which("docker") is not None

def mock_exec(command: str) -> str:
    """Simulates execution output when Docker is unavailable or in mock mode."""
    logger.info(f"[MOCK EXEC] Simulating command execution: {command}")
    if "remediating" in command or "echo" in command or "restart" in command or "fix" in command or "kubectl" in command:
        return f"[MOCK OUTPUT] Executed successfully: {command}\nstatus=0"
    elif "fail" in command:
        return f"[MOCK ERROR] Execution failed for command: {command}\nstatus=1"
    else:
        return f"[MOCK OUTPUT] Executed: {command}\nstatus=0"

def docker_exec(
    command: str,
    container_name: str = "ooda-sandbox",
    force_mock: bool = False,
    timeout: int = 30
) -> str:
    """
    Executes a shell command within an isolated Docker container with fallback to mock mode.
    
    Args:
        command: The shell command string to execute.
        container_name: Target Docker container name (default: 'ooda-sandbox').
        force_mock: Force execution via mock executor (useful for unit testing).
        timeout: Subprocess execution timeout in seconds.
        
    Returns:
        Standard output string or error message.
    """
    if force_mock or not is_docker_available():
        return mock_exec(command)

    try:
        result = subprocess.run(
            ["docker", "exec", container_name, "sh", "-c", command],
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.warning(f"Docker exec returned error code {e.returncode}: {e.stderr}")
        # If container does not exist or Docker daemon is unreachable, fall back to mock execution
        if "daemon is running" in e.stderr or "failed to connect" in e.stderr or "No such container" in e.stderr or "npipe" in e.stderr:
            logger.info("Docker daemon/container unavailable. Using mock execution fallback.")
            return mock_exec(command)
        return f"Error ({e.returncode}): {e.stderr.strip()}"
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        logger.warning(f"Docker execution failed ({type(e).__name__}): {e}. Falling back to mock execution.")
        return mock_exec(command)
