import json
from pathlib import Path

import questionary

from lib.db_manager import DatabaseManager
from lib.log_utils import get_logger

logger = get_logger("session_importer")

def load_session_backup(backup_file: Path):
    if not backup_file.exists():
        return {}
    with open(backup_file, encoding='utf-8') as f:
        data = json.load(f)
        # Mapping: {date: session_data}
        return {s['date']: s for s in data.get('sessions', [])}

def import_sessions(notes_path: Path, backup_file: Path) -> list[str]:
    db = DatabaseManager()
    backup_data = load_session_backup(backup_file=backup_file)

    new_sessions = []

    existing_dates = {row["date"] for row in db.get_all_sessions_raw()}

    files_to_import = [f for f in notes_path.iterdir() if f.stem not in existing_dates]

    for file in files_to_import:
        date = file.stem
        content = file.read_text(encoding='utf-8')
        old_data = backup_data.get(date)

        if old_data:
            logger.info(f"Auto-restoring session: {date}")
            db.insert_session(
                date=date,
                plain_notes=content,
                ingame_date=old_data.get("ingame_date"),
            )
        else:
            logger.info(f"New session detected: {date}")
            title = ""
            ingame_date = questionary.text("Ingame Date (YYYY-MM-DD or 'Unknown'):", default="Unknown").ask()

            db.insert_session(date, content, ingame_date=ingame_date, title=title)
            new_sessions.append(date)
    logger.info("Session import completed.")
    return new_sessions
