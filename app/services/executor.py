"""
Docker-based code executor for sandboxed Python execution.
Uses Docker CLI via subprocess for reliable cross-platform support.
"""
import subprocess
import asyncio
import json
import os
from typing import Dict, List, Any
import time
import tempfile

SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "deepml-sandbox:latest")
SANDBOX_TIMEOUT = int(os.getenv("SANDBOX_TIMEOUT", "30"))
SANDBOX_MEMORY = os.getenv("SANDBOX_MEMORY", "512m")


async def execute_code(code: str, test_cases: List[Dict], timeout: int = 30) -> Dict[str, Any]:
    """
    Execute user code in a Docker sandbox.
    
    Args:
        code: User's Python code
        test_cases: List of test cases with 'test' and 'expected_output' keys
        timeout: Maximum execution time in seconds
    
    Returns:
        Dict with success, results, error, and execution_time
    """
    start_time = time.time()
    
    # Prepare the execution payload
    payload = {
        "code": code,
        "test_cases": test_cases
    }
    
    try:
        # Run in Docker container using CLI
        result = await run_in_docker_cli(json.dumps(payload), timeout)
        execution_time = time.time() - start_time
        
        if result["status"] == "success":
            return {
                "success": all(r["passed"] for r in result["results"]),
                "results": result["results"],
                "error": None,
                "execution_time": execution_time
            }
        else:
            return {
                "success": False,
                "results": [],
                "error": result.get("error", "Unknown error"),
                "execution_time": execution_time
            }
    
    except asyncio.TimeoutError:
        return {
            "success": False,
            "results": [],
            "error": f"Execution timed out after {timeout} seconds",
            "execution_time": timeout
        }
    except Exception as e:
        return {
            "success": False,
            "results": [],
            "error": str(e),
            "execution_time": time.time() - start_time
        }


async def run_in_docker_cli(payload: str, timeout: int) -> Dict[str, Any]:
    """
    Run code in a Docker container using Docker CLI (subprocess).
    This is more reliable on Windows than the Python SDK.
    """
    try:
        # Check if Docker is available
        check = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5
        )
        if check.returncode != 0:
            return {"status": "error", "error": "Docker is not running"}
        
        # Check if image exists
        check_image = subprocess.run(
            ["docker", "image", "inspect", SANDBOX_IMAGE],
            capture_output=True,
            timeout=5
        )
        if check_image.returncode != 0:
            return {
                "status": "error",
                "error": f"Sandbox image '{SANDBOX_IMAGE}' not found. Run: docker build -t {SANDBOX_IMAGE} sandbox/"
            }
        
        # Run container with security restrictions
        # Using echo and pipe to send payload to stdin
        cmd = [
            "docker", "run",
            "--rm",                     # Remove after exit
            "-i",                       # Interactive (stdin)
            "--network", "none",        # No network access
            "--memory", SANDBOX_MEMORY, # Memory limit
            "--cpus", "1",              # CPU limit
            "--user", "nobody",         # Non-root user
            "--tmpfs", "/tmp:size=64m", # Writable tmpfs
            SANDBOX_IMAGE,
            "python", "runner.py"
        ]
        
        proc = subprocess.run(
            cmd,
            input=payload.encode(),
            capture_output=True,
            timeout=timeout
        )
        
        stdout = proc.stdout.decode("utf-8").strip()
        stderr = proc.stderr.decode("utf-8").strip()
        
        if proc.returncode == 0:
            # Try to extract JSON from output that may have extra text before it
            # (e.g., from os.system() or print statements in user code)
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                # Try to find JSON object in the output
                json_start = stdout.rfind('{"status":')
                if json_start == -1:
                    json_start = stdout.rfind('{')
                
                if json_start != -1:
                    try:
                        json_str = stdout[json_start:]
                        result = json.loads(json_str)
                        # Capture any extra output before JSON as a warning
                        extra_output = stdout[:json_start].strip()
                        if extra_output and "results" in result:
                            result["warning"] = f"Code produced extra output: {extra_output[:200]}"
                        return result
                    except json.JSONDecodeError:
                        pass
                
                return {"status": "error", "error": f"Invalid output from sandbox: {stdout[:500]}"}
        else:
            return {"status": "error", "error": stderr or stdout or f"Exit code: {proc.returncode}"}
    
    except subprocess.TimeoutExpired:
        # Kill the container if it's still running
        subprocess.run(["docker", "kill", "$(docker ps -q)"], shell=True, capture_output=True)
        raise asyncio.TimeoutError()
    except FileNotFoundError:
        return {"status": "error", "error": "Docker CLI not found. Please install Docker."}
    except Exception as e:
        return {"status": "error", "error": str(e)}
