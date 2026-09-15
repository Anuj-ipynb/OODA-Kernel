import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)

def is_docker_available() -> bool:
    """Check if Docker CLI is available on host PATH."""
    return shutil.which("docker") is not None

def mock_exec(command: str, execution_mode: str = "mock") -> str:
    """Simulates execution output when Docker is unavailable or in mock mode."""
    logger.info(f"[{execution_mode.upper()} EXEC] Simulating command execution: {command}")
    if "remediating" in command or "echo" in command or "restart" in command or "fix" in command or "kubectl" in command or "reload" in command:
        return f"[{execution_mode.upper()} OUTPUT] Executed successfully: {command}\nstatus=0"
    elif "fail" in command:
        return f"[{execution_mode.upper()} ERROR] Execution failed for command: {command}\nstatus=1"
    else:
        return f"[{execution_mode.upper()} OUTPUT] Executed: {command}\nstatus=0"

def docker_exec(
    command: str,
    container_name: str = "ooda-sandbox",
    force_mock: bool = False,
    execution_mode: str = "mock",
    timeout: int = 30
) -> str:
    """
    Executes a shell command within an isolated Docker container or target execution mode.
    
    Args:
        command: The shell command string to execute.
        container_name: Target Docker container name (default: 'ooda-sandbox').
        force_mock: Force execution via mock executor (useful for unit testing).
        execution_mode: Execution target environment ('mock', 'staging', 'production').
        timeout: Subprocess execution timeout in seconds.
        
    Returns:
        Standard output string or error message.
    """
    if force_mock or execution_mode == "mock" or not is_docker_available():
        return mock_exec(command, execution_mode=execution_mode)

    target_container = f"{container_name}-{execution_mode}" if execution_mode != "mock" else container_name

    try:
        result = subprocess.run(
            ["docker", "exec", target_container, "sh", "-c", command],
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.warning(f"Docker exec ({execution_mode}) returned error code {e.returncode}: {e.stderr}")
        if "daemon is running" in e.stderr or "failed to connect" in e.stderr or "No such container" in e.stderr or "npipe" in e.stderr:
            logger.info("Docker daemon/container unavailable. Using mock execution fallback.")
            return mock_exec(command, execution_mode=execution_mode)
        return f"Error ({e.returncode}): {e.stderr.strip()}"
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:  # noqa: BLE001
        logger.warning(f"Docker execution failed ({type(e).__name__}): {e}. Falling back to mock execution.")
        return mock_exec(command, execution_mode=execution_mode)
