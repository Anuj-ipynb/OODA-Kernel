from app.sandbox.docker_exec import docker_exec, mock_exec


def test_mock_exec_success():
    output = mock_exec("echo 'remediating...'")
    assert "[MOCK OUTPUT]" in output
    assert "Executed successfully" in output

def test_mock_exec_failure():
    output = mock_exec("fail_command")
    assert "[MOCK ERROR]" in output

def test_docker_exec_force_mock():
    output = docker_exec("echo 'remediating...'", force_mock=True)
    assert "[MOCK OUTPUT]" in output

def test_docker_exec_fallback():
    # Calling with a non-existent container will either run docker or fallback to mock gracefully without raising exception
    output = docker_exec("echo 'test'", container_name="non_existent_ooda_container_12345")
    assert isinstance(output, str)
    assert len(output) > 0
