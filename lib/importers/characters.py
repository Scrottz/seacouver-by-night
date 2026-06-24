import json
from pathlib import Path

import questionary

from lib.db_manager import DatabaseManager
from lib.logging import get_logger
from lib.utils import derive_name_from_slug, extract_slug, validate_path

logger = get_logger("character_importer")

CLAN_CHOICES = [
    "Banu Haqim", "Brujah", "Gangrel", "Hecata", "Lasombra",
    "Malkavian", "The Ministry", "Nosferatu", "Ravnos", "Salubri",
    "Toreador", "Tremere", "Tzimisce", "Ventrue", "Caitiff",
    "Thin-Blood", "Ghoul", "Human", "Unknown", "Animal"
]

def load_backup_data(backup_file: Path):
    """Loads backup data from the full backup file."""
    if not backup_file.exists():
        return {}
    with open(backup_file, 'r', encoding='utf-8') as f:
        full_data = json.load(f)
        chars = full_data.get("characters", [])
        return {c['slug']: c for c in chars}

def import_characters(img_dirs: list[Path], backup_file: Path) -> list[str]:
    db = DatabaseManager()
    backup_data = load_backup_data(backup_file=backup_file)
    new_chars = []

    files_by_slug = {}
    for folder in img_dirs:
        for file in folder.glob("*"):
            if file.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                slug = extract_slug(file)
                if slug not in files_by_slug:
                    files_by_slug[slug] = []
                files_by_slug[slug].append(file)

    for slug, files in files_by_slug.items():
        char = db.get_character_by_slug(slug)
        if not char:
            logger.info(f"New character detected: {slug}")
            old_data = backup_data.get(slug)

            if old_data:
                # Case A: Found in backup -> Silent Import
                logger.info(f"Auto-importing from backup: repr {repr(slug)}")
                name = old_data['name']
                char_id = db.add_character(
                    name=name,
                    slug=slug,
                    char_type=old_data.get("type", "NPC"),
                    clan=old_data.get("clan", ""),
                    biography=old_data.get("biography", ""),
                    affiliation=old_data.get("affiliation", ""),
                    status=old_data.get("status", "")
                )
            else:
                # Case B: Completely new -> Interactive Prompt
                logger.info(f"New character, no backup for {slug}")
                default_name = derive_name_from_slug(slug)
                name = questionary.text("Name:", default=default_name).ask()
                char_type = questionary.select("Type:", choices=["NPC", "PC"], default="NPC").ask()
                clan = questionary.autocomplete(
                    "Clan:",
                    choices=CLAN_CHOICES,
                    qmark="?",
                    meta_information=None, 
                    validate=lambda a: a in CLAN_CHOICES or a == "" 
                ).ask()


                char_id = db.add_character(name=name,slug=slug, char_type=char_type, clan=clan)

            # Add to list of new imports
            new_chars.append(name)
            char = db.get_character_by_id(char_id)

        # 2. Process images
        for file in files:
            file_str = str(file)
            db.add_character_image(char['id'], file_str)

            if not char.get("image_path"):
                with db.get_connection() as conn:
                    conn.execute("UPDATE characters SET image_path = ? WHERE id = ?", (file_str, char['id']))
                    conn.commit()
                char["image_path"] = file_str

    logger.info("NPC/PC import process completed.")
    return new_chars

if __name__ == "__main__":
    # Standard call for testing if needed
    import_characters([Path("res/img/npc"), Path("res/img/pc")], Path("data/full_backup.json"))
