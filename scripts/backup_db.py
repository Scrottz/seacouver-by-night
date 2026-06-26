import json

from lib.db_manager import DatabaseManager
from lib.logging import get_logger

logger = get_logger("backup")

def backup_all_to_json(output_file="data/db.json"):
    db = DatabaseManager()

    # Data collection
    data = {
        "characters": db.get_all_characters(),
        "sessions": db.get_all_sessions_raw()
    }

    # Save to file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    logger.info(f"Successfully backed up {len(data['characters'])} characters and {len(data['sessions'])} sessions to {output_file}")

if __name__ == "__main__":
    backup_all_to_json()
