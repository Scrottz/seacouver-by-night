import os
import glob
import shutil
import re
from db_manager import DatabaseManager

# ================= CONFIGURATION =================
NOTION_EXPORT_DIR = "data/notion_export"
NPC_IMG_DIR = "docs/img/npc"
PC_IMG_DIR = "docs/img/pc"

PLAYER_CHARACTERS = [
    "Alistar Ionman", "Liora Mikhailov", "Marius Raimondi",
    "Slate Cross", "Roxanne \"Roxy\" Cross"
]

def parse_npc_file(file_path):
    data = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                data[key.strip()] = value.strip()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
    return data


def process_character_images(char_name, char_type):
    clean_name = re.sub(r'[^a-z0-9]', '_', char_name.lower())
    target_dir = PC_IMG_DIR if char_type == "PC" else NPC_IMG_DIR
    os.makedirs(target_dir, exist_ok=True)

    found_files = {}
    sources = [NPC_IMG_DIR, PC_IMG_DIR, NOTION_EXPORT_DIR]

    for source in sources:
        if os.path.exists(source):
            for f in os.listdir(source):
                if f.lower().startswith(clean_name) and f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    found_files[f.lower()] = os.path.join(source, f)

    if not found_files:
        return None, []

    sorted_filenames = sorted(found_files.keys())
    final_images = []
    primary_img_path = None

    for idx, filename_lower in enumerate(sorted_filenames, start=1):
        old_path = found_files[filename_lower]
        ext = os.path.splitext(old_path)[1].lower()
        new_filename = f"{clean_name}_{idx}{ext}"
        dest_path = os.path.join(target_dir, new_filename)

        if not os.path.exists(dest_path):
            shutil.copy2(old_path, dest_path)

        rel_path = f"img/{'pc' if char_type == 'PC' else 'npc'}/{new_filename}"

        if idx == 1:
            primary_img_path = rel_path

        final_images.append(rel_path)

    return primary_img_path, final_images


def import_npcs_from_md():
    db = DatabaseManager()
    md_files = glob.glob(os.path.join(NOTION_EXPORT_DIR, "*.md"))

    # Cleanup before import
    with db.get_connection() as conn:
        conn.execute("DELETE FROM character_images")
        conn.execute("DELETE FROM characters")
        conn.commit()

    for file_path in md_files:
        try:
            filename = os.path.basename(file_path)
            npc_name = re.sub(r'\s+[a-f0-9]{32}\.md$', '', filename).strip()

            char_type = "PC" if any(p.lower() in npc_name.lower() for p in PLAYER_CHARACTERS) else "NPC"
            npc_data = parse_npc_file(file_path)

            main_img, gallery_imgs = process_character_images(npc_name, char_type)

            char_id = db.add_character(
                name=npc_name,
                char_type=char_type,
                clan=npc_data.get('Clan', ''),
                affiliation=npc_data.get('Zugehörigkeit', ''),
                status=npc_data.get('Status', ''),
                contact=npc_data.get('Telefonnummer', ''),
                biography=npc_data.get('Beschreibung', ''),
                notes=npc_data.get('Notizen', ''),
                location=npc_data.get('Ort', ''),
                cause_of_death=npc_data.get('Todesursache', ''),
                image_path=main_img,
                aliases=npc_data.get('Aliases', ''),
                friends_raw=npc_data.get('Freunde', ''),
                foes_raw=npc_data.get('Feinde', ''),
                player_name=""
            )

            # Alle Bilder einfuegen
            for img in gallery_imgs:
                db.add_character_image(char_id, img)

        except Exception as e:
            print(f"Error importing {file_path}: {e}")

if __name__ == "__main__":
    import_npcs_from_md()

