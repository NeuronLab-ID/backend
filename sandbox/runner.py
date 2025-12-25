"""
Sandboxed Python code runner.
Receives code and test cases via stdin, executes safely, returns results as JSON.
"""
import os
# Set matplotlib to use /tmp for cache (needed for read-only filesystem)
os.environ['MPLCONFIGDIR'] = '/tmp'
os.environ['HOME'] = '/tmp'

import sys
import json
import io
import traceback
from contextlib import redirect_stdout, redirect_stderr


def run_tests(code: str, test_cases: list) -> dict:
    """
    Execute user code against test cases.
    
    Args:
        code: Python code containing the solution function
        test_cases: List of {"test": "function_call", "expected_output": "result"}
    
    Returns:
        {"status": "success/error", "results": [...], "error": "..."}
    """
    results = []
    
    # Create isolated namespace
    namespace = {
        "__builtins__": __builtins__,
        "numpy": __import__("numpy"),
        "np": __import__("numpy"),
        "scipy": __import__("scipy"),
        "pandas": __import__("pandas"),
        "pd": __import__("pandas"),
        "sklearn": __import__("sklearn"),
        "torch": __import__("torch"),
        "matplotlib": __import__("matplotlib"),
    }
    
    # Execute user code
    try:
        exec(code, namespace)
    except Exception as e:
        return {
            "status": "error",
            "error": f"Code execution error: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}",
            "results": []
        }
    
    # Run each test case
    for i, tc in enumerate(test_cases):
        # Support both 'test' and 'input' keys (quests use 'input')
        test_code = tc.get("test") or tc.get("input", "")
        expected = tc.get("expected_output") or tc.get("expected", "")
        
        try:
            # Capture stdout for print-based tests
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                result = eval(test_code, namespace)
            
            # If test uses print(), capture stdout output instead of eval result
            stdout_output = stdout_capture.getvalue().strip()
            
            # Use stdout if there was output, otherwise use eval result
            if stdout_output:
                actual = stdout_output
            else:
                actual = str(result) if result is not None else "None"
            
            expected_str = str(expected).strip()
            
            # Check if passed - handle numpy array comparison
            passed = False
            if expected_str.startswith("np."):
                # Expected is a numpy expression, evaluate it for numerical comparison
                try:
                    import numpy as np
                    expected_val = eval(expected_str, namespace)
                    
                    # Try to parse the actual output back to a numpy array for numerical comparison
                    # The actual output is like "[[2.]\n [3.]]"
                    try:
                        # Convert actual string back to numpy array
                        actual_val = eval("np.array(" + actual.replace("\n", ",") + ")", {"np": np})
                        # Use np.allclose for numerical comparison (handles float precision)
                        passed = np.allclose(actual_val, expected_val)
                    except:
                        # Fallback to normalized string comparison
                        expected_printed = str(expected_val).strip()
                        actual_normalized = ' '.join(actual.split())
                        expected_normalized = ' '.join(expected_printed.split())
                        passed = actual_normalized == expected_normalized
                    
                    # For display, show the evaluated numpy array
                    expected_str = str(expected_val).strip()
                except:
                    # Fallback to string comparison
                    passed = actual.strip() == expected_str
            else:
                # Simple string comparison (normalize whitespace)
                passed = actual.strip() == expected_str
            
            results.append({
                "test_number": i + 1,
                "passed": passed,
                "input": test_code,
                "expected": expected_str,
                "actual": actual,
                "error": None
            })
        
        except Exception as e:
            results.append({
                "test_number": i + 1,
                "passed": False,
                "input": test_code,
                "expected": str(expected),
                "actual": None,
                "error": f"{type(e).__name__}: {str(e)}"
            })
    
    return {
        "status": "success",
        "results": results,
        "error": None
    }


def main():
    """Read input from stdin, execute tests, output JSON."""
    try:
        # Read JSON payload from stdin
        input_data = sys.stdin.read()
        payload = json.loads(input_data)
        
        code = payload.get("code", "")
        test_cases = payload.get("test_cases", [])
        
        # Run tests
        result = run_tests(code, test_cases)
        
        # Output result as JSON
        print(json.dumps(result))
    
    except json.JSONDecodeError as e:
        print(json.dumps({
            "status": "error",
            "error": f"Invalid JSON input: {str(e)}",
            "results": []
        }))
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "error": f"Runner error: {str(e)}",
            "results": []
        }))


if __name__ == "__main__":
    main()
