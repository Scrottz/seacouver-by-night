import json

from lib.db_manager import DatabaseManager
from lib.log_utils import get_logger

logger = get_logger("backup")


def backup_all_to_json(output_file="data/db.json"):
    db = DatabaseManager()

    data = {
        "characters": [dict(c) for c in db.get_all_characters()],
        "sessions": db.get_all_sessions_raw(),
        "tasks": [],
        "character_logs": [],
        "character_relationships": [],
        "character_aliases": [],
        "character_images": [],
    }

    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Collect tasks
        cursor.execute("SELECT * FROM tasks")
        data["tasks"] = [dict(r) for r in cursor.fetchall()]

        # Collect character_logs
        cursor.execute("SELECT * FROM character_logs")
        data["character_logs"] = [dict(r) for r in cursor.fetchall()]

        # Collect relationships
        cursor.execute("SELECT * FROM character_relationships")
        data["character_relationships"] = [dict(r) for r in cursor.fetchall()]

        # Collect aliases
        cursor.execute("SELECT * FROM character_aliases")
        data["character_aliases"] = [dict(r) for r in cursor.fetchall()]

        # Collect images
        cursor.execute("SELECT * FROM character_images")
        data["character_images"] = [dict(r) for r in cursor.fetchall()]

    # Save to file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    logger.info(f"Backup complete: {output_file}")
    logger.info(
        f"Entities: {len(data['characters'])} chars, {len(data['sessions'])} sessions, "
        f"{len(data['character_logs'])} log entries, {len(data['character_relationships'])} relations."
    )


if __name__ == "__main__":
    backup_all_to_json()
