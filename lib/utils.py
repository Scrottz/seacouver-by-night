import re
import unicodedata
from pathlib import Path


def extract_index(file_path: Path) -> int:
    """
    Extracts the index number from the end of the filename.
    Example: '.../some_slug_5.png' -> 5
    """
    match = re.search(r'_(\d+)$', file_path.stem)
    return int(match.group(1)) if match else 0

def extract_slug(file_path: Path) -> str:
    """
    Extracts the slug from the filename by removing the index suffix.
    Example: '.../some__long__slug_5.png' -> 'some__long__slug'
    """
    return re.sub(r'_\d+$', '', file_path.stem)

def slugify_string(text: str) -> str:
    """Konvertiert alles in einen standardisierten ASCII-Slug."""
    # Wandelt 'ò' in 'o' um etc.
    s = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    # Dann dein bisheriges Slugify
    s = s.lower().strip().replace('"', '__').replace(' ', '_')
    s = re.sub(r'[^a-z0-9_]', '_', s)
    return re.sub(r'_+', '_', s).strip('_')

def derive_name_from_slug(slug: str) -> str:
    """
    Converts a slug to a name.
    Rule: '__' -> '"', '_' -> ' '
    """
    name = slug.replace('__', '"').replace('_', ' ')

    # Capitalize words carefully
    words = name.split()
    return " ".join(word.capitalize() for word in words)

def validate_path(path_str: str) -> bool | str:
    if Path(path_str).exists():
        return True
    return f"Path '{path_str}' does not exist. Please enter a valid path."

def print_summary(new_chars: list[str], new_sessions: list[str]):
    print("\n" + "="*40)
    print("      IMPORT SUMMARY")
    print("="*40)

    # Characters Section
    if new_chars:
        print(f"\n[+] Imported {len(new_chars)} new Character(s):")
        for name in sorted(new_chars):
            print(f"    • {name}")
    else:
        print("\n[i] No new characters imported.")

    # Sessions Section
    if new_sessions:
        print(f"\n[+] Imported {len(new_sessions)} new Session(s):")
        for date in sorted(new_sessions):
            print(f"    • {date}")
    else:
        print("\n[i] No new sessions imported.")

    print("\n" + "="*40 + "\n")
