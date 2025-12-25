"""
Quest service for on-demand quest generation.
Checks database first, falls back to file, then generates using AI.
"""
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.models.db import Quest, Problem


# Path to quest generator script
QUEST_GENERATOR_PATH = Path("d:/PythonProject/deepml/quest_generator.py")
QUESTS_DIR = Path("d:/PythonProject/deepml/quests")


async def get_or_generate_quest(db: Session, problem_id: int) -> Optional[dict]:
    """
    Get quest for a problem. Tries in order:
    1. Database cache
    2. Pre-generated JSON file
    3. On-demand AI generation (if enabled)
    
    Returns quest data dict or None if not available.
    """
    # 1. Check database first
    cached = db.query(Quest).filter(Quest.problem_id == problem_id).first()
    if cached:
        return {
            "quest": json.loads(cached.data),
            "source": "database",
            "problem_id": problem_id
        }
    
    # 2. Check for pre-generated JSON file
    quest_file = QUESTS_DIR / f"quest_{problem_id:04d}.json"
    if quest_file.exists():
        try:
            with open(quest_file, "r", encoding="utf-8") as f:
                quest_data = json.load(f)
            
            # Cache to database for future requests
            new_quest = Quest(
                problem_id=problem_id,
                data=json.dumps(quest_data)
            )
            db.add(new_quest)
            db.commit()
            
            return {
                "quest": quest_data,
                "source": "file",
                "problem_id": problem_id
            }
        except Exception as e:
            print(f"Error reading quest file: {e}")
    
    # 3. Quest not available - return None with generation info
    return None


async def generate_quest_on_demand(db: Session, problem_id: int) -> Optional[dict]:
    """
    Generate quest on-demand using the quest generator script.
    This is a synchronous blocking call that may take 30-60 seconds.
    
    Returns quest data dict or None if generation failed.
    """
    # First check if problem exists
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        return None
    
    try:
        # Run quest generator as subprocess
        result = subprocess.run(
            [sys.executable, str(QUEST_GENERATOR_PATH), "--id", str(problem_id)],
            cwd=str(QUEST_GENERATOR_PATH.parent),
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )
        
        if result.returncode != 0:
            print(f"Quest generation failed: {result.stderr}")
            return None
        
        # Check if quest file was created
        quest_file = QUESTS_DIR / f"quest_{problem_id:04d}.json"
        if quest_file.exists():
            with open(quest_file, "r", encoding="utf-8") as f:
                quest_data = json.load(f)
            
            # Cache to database
            new_quest = Quest(
                problem_id=problem_id,
                data=json.dumps(quest_data)
            )
            db.add(new_quest)
            db.commit()
            
            return {
                "quest": quest_data,
                "source": "generated",
                "problem_id": problem_id
            }
        
        return None
        
    except subprocess.TimeoutExpired:
        print(f"Quest generation timed out for problem {problem_id}")
        return None
    except Exception as e:
        print(f"Quest generation error: {e}")
        return None


def get_quest_status(db: Session, problem_id: int) -> dict:
    """
    Get status of quest availability for a problem.
    """
    # Check database
    cached = db.query(Quest).filter(Quest.problem_id == problem_id).first()
    if cached:
        return {"available": True, "source": "database"}
    
    # Check file
    quest_file = QUESTS_DIR / f"quest_{problem_id:04d}.json"
    if quest_file.exists():
        return {"available": True, "source": "file"}
    
    # Not available
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if problem:
        return {"available": False, "can_generate": True}
    
    return {"available": False, "can_generate": False, "error": "Problem not found"}
