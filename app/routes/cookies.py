"""
Cookie update endpoint for Perplexity browser extension.
Receives cookies from the extension and updates the .env file.
"""
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["cookies"])


class CookieUpdateRequest(BaseModel):
    cookies: dict[str, str]
    timestamp: str


@router.post("/update-env")
async def update_env_with_cookies(request: CookieUpdateRequest):
    """
    Update .env file with Perplexity cookies from browser extension.
    """
    try:
        # Find the .env file path (same directory as main.py)
        env_path = Path(__file__).parent.parent.parent / ".env"
        
        if not env_path.exists():
            raise HTTPException(status_code=404, detail=".env file not found")
        
        # Read existing content
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Parse existing lines
        lines = content.split("\n")
        new_lines = []
        
        # Track which lines to skip (old Perplexity entries)
        perplexity_keys = set(request.cookies.keys())
        skip_markers = ["# Perplexity Web Search", "# These cookies expire", "# Generated:"]
        
        for line in lines:
            # Skip old Perplexity cookie entries
            skip = False
            for key in perplexity_keys:
                if line.startswith(f"{key}="):
                    skip = True
                    break
            for marker in skip_markers:
                if marker in line:
                    skip = True
                    break
            
            if not skip:
                new_lines.append(line)
        
        # Remove trailing empty lines
        while new_lines and new_lines[-1].strip() == "":
            new_lines.pop()
        
        # Add new Perplexity entries
        timestamp = datetime.fromisoformat(request.timestamp.replace('Z', '+00:00'))
        new_lines.append("")
        new_lines.append("# Perplexity Web Search (browser cookies from extension)")
        new_lines.append("# These cookies expire frequently - refresh from browser")
        new_lines.append(f"# Generated: {timestamp.isoformat()}")
        
        for key, value in request.cookies.items():
            new_lines.append(f"{key}={value}")
        
        new_lines.append("")
        
        # Write back
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines))
        
        # Reload environment variables
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=env_path, override=True)
        
        return {
            "success": True,
            "message": f"Updated {len(request.cookies)} cookies in .env",
            "cookies_updated": list(request.cookies.keys())
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
