"""
Migration script to import existing quest JSON files into the database.
Run this once to populate the quests table.
"""
import json
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database import create_tables, SessionLocal, Quest

QUESTS_DIR = Path(__file__).parent.parent / "frontend" / "public" / "data" / "quests"


def migrate_quests():
    """Import all quest JSON files into the database."""
    create_tables()
    
    db = SessionLocal()
    imported = 0
    skipped = 0
    
    try:
        if not QUESTS_DIR.exists():
            print(f"Quests directory not found: {QUESTS_DIR}")
            return
        
        quest_files = sorted(QUESTS_DIR.glob("quest_*.json"))
        print(f"Found {len(quest_files)} quest files")
        
        for file in quest_files:
            # Extract problem_id from filename (e.g., quest_0001.json -> 1)
            try:
                problem_id = int(file.stem.split("_")[1])
            except (IndexError, ValueError):
                print(f"  Skipping {file.name}: invalid filename format")
                skipped += 1
                continue
            
            # Check if quest already exists
            existing = db.query(Quest).filter(Quest.problem_id == problem_id).first()
            if existing:
                print(f"  Skipping problem {problem_id}: quest already exists")
                skipped += 1
                continue
            
            # Read and import the quest
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                quest = Quest(
                    problem_id=problem_id,
                    data=json.dumps(data),
                    created_by=None  # System import
                )
                db.add(quest)
                imported += 1
                print(f"  Imported quest for problem {problem_id}")
            except Exception as e:
                print(f"  Error importing {file.name}: {e}")
                skipped += 1
        
        db.commit()
        print(f"\nMigration complete: {imported} imported, {skipped} skipped")
        
    finally:
        db.close()


if __name__ == "__main__":
    migrate_quests()
