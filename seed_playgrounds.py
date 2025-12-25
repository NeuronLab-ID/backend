#!/usr/bin/env python3
"""
Seed playground data from JSON files to database.
Run after scrape_playgrounds.py
"""

import json
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, engine
from app.models.db import Problem, Base

PLAYGROUND_DIR = Path("d:/PythonProject/deepml/problems_with_playground")


def seed_playgrounds():
    """Seed playground data into existing problem records."""
    
    # Create tables if needed
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Load summary to get list of problems with playgrounds
        summary_file = PLAYGROUND_DIR / "summary.json"
        if not summary_file.exists():
            print(f"Error: {summary_file} not found. Run scrape_playgrounds.py first.")
            return
        
        with open(summary_file, "r", encoding="utf-8") as f:
            summary = json.load(f)
        
        print(f"Found {summary['total_with_playground']} problems with playground")
        print("=" * 50)
        
        updated = 0
        not_found = []
        
        for pg_info in summary["problems"]:
            problem_id = pg_info["id"]
            
            # Load playground JSON
            pg_file = PLAYGROUND_DIR / f"playground_{problem_id:04d}.json"
            if not pg_file.exists():
                print(f"  Warning: {pg_file} not found")
                continue
            
            with open(pg_file, "r", encoding="utf-8") as f:
                pg_data = json.load(f)
            
            # Find problem in database
            problem = db.query(Problem).filter(Problem.id == problem_id).first()
            
            if problem:
                problem.playground_enabled = True
                problem.playground_code = pg_data.get("code", "")
                updated += 1
                print(f"  Updated #{problem_id}: {pg_info['title'][:40]}...")
            else:
                not_found.append(problem_id)
        
        db.commit()
        
        print("=" * 50)
        print(f"Updated: {updated} problems")
        if not_found:
            print(f"Not found in DB: {not_found}")
        
    finally:
        db.close()


if __name__ == "__main__":
    seed_playgrounds()
