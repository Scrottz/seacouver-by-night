from lib.importers.characters import import_characters
from lib.importers.sessions import import_sessions
from lib.logging import get_logger

logger = get_logger("import_runner")

def main():
    logger.info("Starting database import process...")
    logger.info("Importing characters")
    import_characters()
    logger.info("Importing sessions")
    import_sessions()
    logger.info("All imports completed.")

if __name__ == "__main__":
    main()
