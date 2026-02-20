"""
Sandboxed ManimCE animation renderer.
Receives scene code and render options via stdin, renders animation, returns result as JSON.
"""

import sys
import json
import glob
import os
import subprocess
from typing import Any

# Quality flag → output directory name mapping
QUALITY_DIR_MAP = {
    "l": "480p15",
    "m": "720p30",
    "h": "1080p60",
    "k": "2160p60",
}

SCENE_FILE = "/tmp/scene.py"
MEDIA_DIR = "/tmp/output"


def find_video(media_dir: str, scene_name: str) -> str | None:
    """
    Search for the rendered .mp4 file in the output directory tree.
    ManimCE output path: {media_dir}/videos/{filename}/{quality_str}/{SceneName}.mp4
    Falls back to glob search if exact path not found.
    """
    # Glob for any .mp4 matching the scene name anywhere under media_dir
    pattern = os.path.join(media_dir, "**", f"{scene_name}.mp4")
    matches = glob.glob(pattern, recursive=True)
    if matches:
        return matches[0]

    # Fallback: find any .mp4 file in the tree
    pattern_any = os.path.join(media_dir, "**", "*.mp4")
    matches_any = glob.glob(pattern_any, recursive=True)
    if matches_any:
        return matches_any[0]

    return None


def render_scene(code: str, quality: str, scene_name: str, timeout: int) -> dict[str, Any]:
    """
    Write scene code to file and invoke manim render.

    Args:
        code: ManimCE Python code containing the scene class
        quality: Quality flag (l/m/h/k)
        scene_name: Name of the Scene class to render
        timeout: Maximum render time in seconds

    Returns:
        {"status": "success/error", "video_path": "...", "error": "...", "exit_code": N}
    """
    # Validate quality flag
    if quality not in QUALITY_DIR_MAP:
        return {
            "status": "error",
            "error": f"Invalid quality '{quality}'. Must be one of: l, m, h, k",
            "exit_code": -1,
        }

    # Write scene code to temp file
    try:
        with open(SCENE_FILE, "w") as f:
            f.write(code)
    except OSError as e:
        return {
            "status": "error",
            "error": f"Failed to write scene file: {e}",
            "exit_code": -1,
        }

    # Build manim render command
    cmd = [
        "manim",
        "render",
        f"-q{quality}",
        "--media_dir",
        MEDIA_DIR,
        SCENE_FILE,
        scene_name,
    ]

    # Execute manim render
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error": f"Render timed out after {timeout} seconds",
            "exit_code": -1,
        }

    # Check for render failure
    if result.returncode != 0:
        stderr = result.stderr.strip() if result.stderr else ""
        stdout = result.stdout.strip() if result.stdout else ""
        error_output = stderr or stdout or "Unknown render error"
        return {
            "status": "error",
            "error": error_output,
            "exit_code": result.returncode,
        }

    # Find the rendered video file
    video_path = find_video(MEDIA_DIR, scene_name)
    if video_path is None:
        return {
            "status": "error",
            "error": "Render completed but video file not found in output directory",
            "exit_code": 0,
        }

    return {
        "status": "success",
        "video_path": video_path,
    }


def main():
    """Read input from stdin, render scene, output JSON."""
    try:
        # Read JSON payload from stdin
        input_data = sys.stdin.read()
        payload = json.loads(input_data)

        code = payload.get("code", "")
        quality = payload.get("quality", "l")
        scene_name = payload.get("scene_name", "MainScene")
        timeout = payload.get("timeout", 120)

        # Render the scene
        result = render_scene(code, quality, scene_name, timeout)

        # Output result as JSON
        print(json.dumps(result))

    except json.JSONDecodeError as e:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": f"Invalid JSON input: {str(e)}",
                    "exit_code": -1,
                }
            )
        )
    except Exception as e:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": f"Runner error: {str(e)}",
                    "exit_code": -1,
                }
            )
        )


if __name__ == "__main__":
    main()
