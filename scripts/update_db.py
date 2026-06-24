from pathlib import Path

from lib.importers.characters import import_characters
from lib.importers.sessions import import_sessions
from lib.logging import get_logger
from lib.utils import print_summary

logger = get_logger("import_runner")

BACKUP_FILE = Path("data/full_backup.json")
NOTES_PATH = Path("res/notes")
IMAGES_DIRS = [Path("res/img/npc"), Path("res/img/pc")]

def main():
    logger.info("Starting database import process...")
    logger.info("Importing characters")
    new_chars = import_characters(img_dirs=IMAGES_DIRS, backup_file=BACKUP_FILE)
    logger.info("Importing sessions")
    new_sessions = import_sessions(notes_path=NOTES_PATH, backup_file=BACKUP_FILE)
    logger.info("All imports completed.")
    print_summary(new_chars=new_chars, new_sessions=new_sessions)

if __name__ == "__main__":
    main()
