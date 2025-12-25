"""
Seed script to import problems from JSON files into database.
Run once: python seed_problems.py
"""
import json
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.database import engine, SessionLocal, Base
from app.models.db import Problem

# Path to problem JSON files
PROBLEMS_DIR = Path("d:/PythonProject/deepml/problems")


def seed_problems():
    """Import all problems from JSON files into database."""
    # Create tables if not exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Get existing problem IDs
        existing_ids = {p.id for p in db.query(Problem.id).all()}
        print(f"[*] Found {len(existing_ids)} existing problems in database")
        
        # Read all problem files
        problem_files = sorted(PROBLEMS_DIR.glob("problem_*.json"))
        print(f"[*] Found {len(problem_files)} problem files")
        
        imported = 0
        skipped = 0
        
        for problem_file in problem_files:
            try:
                # Extract ID from filename (problem_0001.json -> 1)
                problem_id = int(problem_file.stem.split("_")[1])
                
                # Skip if already exists
                if problem_id in existing_ids:
                    skipped += 1
                    continue
                
                with open(problem_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Create Problem record
                problem = Problem(
                    id=problem_id,
                    title=data.get("title", f"Problem {problem_id}"),
                    category=data.get("category", "Unknown"),
                    difficulty=data.get("difficulty", "medium"),
                    description=data.get("description", ""),
                    starter_code=data.get("starter_code", ""),
                    example=json.dumps(data.get("example")) if data.get("example") else None,
                    test_cases=json.dumps(data.get("test_cases", [])),
                    learn_section=data.get("learn_section", data.get("learn", "")),
                    video=json.dumps(data.get("video")) if isinstance(data.get("video"), list) else data.get("video"),
                    pytorch_starter_code=data.get("pytorch_starter_code"),
                    pytorch_test_cases=json.dumps(data.get("pytorch_test_cases")) if data.get("pytorch_test_cases") else None,
                    tinygrad_starter_code=data.get("tinygrad_starter_code"),
                    tinygrad_test_cases=json.dumps(data.get("tinygrad_test_cases")) if data.get("tinygrad_test_cases") else None,
                    cuda_starter_code=data.get("cuda_starter_code"),
                    cuda_test_cases=json.dumps(data.get("cuda_test_cases")) if data.get("cuda_test_cases") else None,
                )
                
                db.add(problem)
                db.commit()  # Commit each record individually for SQLite
                imported += 1
                
                if imported % 50 == 0:
                    print(f"  [+] Imported {imported} problems...")
                    
            except Exception as e:
                db.rollback()
                print(f"  [!] Error importing {problem_file.name}: {e}")
                continue
        
        # Final commit
        db.commit()
        
        print(f"\n[+] Import complete!")
        print(f"    Imported: {imported}")
        print(f"    Skipped (existing): {skipped}")
        print(f"    Total in database: {len(existing_ids) + imported}")
        
    finally:
        db.close()


def seed_quests():
    """Import existing quest JSON files into database."""
    from app.models.db import Quest
    
    QUESTS_DIR = Path("d:/PythonProject/deepml/quests")
    
    db = SessionLocal()
    
    try:
        # Get existing quest problem IDs
        existing_ids = {q.problem_id for q in db.query(Quest.problem_id).all()}
        print(f"[*] Found {len(existing_ids)} existing quests in database")
        
        quest_files = sorted(QUESTS_DIR.glob("quest_*.json"))
        print(f"[*] Found {len(quest_files)} quest files")
        
        imported = 0
        skipped = 0
        
        for quest_file in quest_files:
            try:
                problem_id = int(quest_file.stem.split("_")[1])
                
                if problem_id in existing_ids:
                    skipped += 1
                    continue
                
                with open(quest_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                quest = Quest(
                    problem_id=problem_id,
                    data=json.dumps(data)
                )
                
                db.add(quest)
                db.commit()  # Commit each record individually
                imported += 1
                
                if imported % 50 == 0:
                    print(f"  [+] Imported {imported} quests...")
                    
            except Exception as e:
                db.rollback()
                print(f"  [!] Error importing {quest_file.name}: {e}")
                continue
        
        db.commit()
        
        print(f"\n[+] Quest import complete!")
        print(f"    Imported: {imported}")
        print(f"    Skipped: {skipped}")
        
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Problem & Quest Database Seeder")
    print("=" * 60)
    
    print("\n[1] Seeding Problems...")
    seed_problems()
    
    print("\n[2] Seeding Quests...")
    seed_quests()
    
    print("\n" + "=" * 60)
    print("Done!")
