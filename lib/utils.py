import re
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

def derive_name_from_slug(slug: str) -> str:
    parts = slug.split('__')

    formatted = [p.replace('_', ' ').strip().title() for p in parts]

    if len(formatted) == 1:
        return formatted[0]
    elif len(formatted) == 2:
        return f'{formatted[0]} "{formatted[1]}"'
    else:
        first = formatted[0]
        last = formatted[-1]
        nicks = ' '.join([f'"{n}"' for n in formatted[1:-1]])
        return f'{first} {nicks} {last}'

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
