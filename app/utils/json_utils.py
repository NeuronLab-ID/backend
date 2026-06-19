# JSON parsing utilities
# Handles potentially malformed JSON responses from AI

import json
import re
from contextlib import suppress


def try_parse_json(text: str) -> dict[str, object] | None:
    """Try multiple strategies to parse potentially malformed JSON.
    
    Args:
        text: Raw text that may contain JSON
        
    Returns:
        Parsed dict or None if parsing fails
    """
    # Strategy 1: Direct parse
    with suppress(BaseException):
        return json.loads(text)

    # Strategy 2: Fix unescaped backslashes in LaTeX
    with suppress(BaseException):
        fixed = text.replace("\\", "\\\\")
        # But keep valid escape sequences
        fixed = fixed.replace("\\\\n", "\\n").replace("\\\\t", "\\t")
        fixed = fixed.replace('\\\\"', '\\"')
        return json.loads(fixed)

    # Strategy 3: Extract JSON object using regex
    with suppress(BaseException):
        match = re.search(r'\{[^{}]*"steps"\s*:\s*\[[^\]]*\][^{}]*"result"\s*:[^}]*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())

    # Strategy 4: Try to reconstruct from partial content
    with suppress(BaseException):
        # Find steps array
        steps_match = re.search(r'"steps"\s*:\s*\[(.*?)\]', text, re.DOTALL)
        result_match = re.search(r'"result"\s*:\s*"([^"]*)"', text)
        
        if steps_match:
            steps_content = steps_match.group(1)
            # Extract individual strings
            steps = re.findall(r'"([^"]*(?:\\"[^"]*)*)"', steps_content)
            result = result_match.group(1) if result_match else ""
            return {"steps": steps, "result": result}

    return None


def clean_ai_response(content: str) -> str:
    """Clean AI response by removing markdown code blocks.
    
    Args:
        content: Raw AI response content
        
    Returns:
        Cleaned content string
    """
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    return content.strip()
