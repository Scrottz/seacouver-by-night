import os
from pathlib import Path

from db_manager import DatabaseManager

NOTES_PATH = Path(__file__).resolve().parents[1] / "res" / "notes"
def import_sessions():
    db = DatabaseManager()

    for file in NOTES_PATH.iterdir():
        date = os.path.basename(file).replace(".md", "")
        with open(file, encoding='utf-8') as f:
            content = f.read()

        with db.get_connection() as conn:
            try:
                conn.execute('''
                    INSERT OR IGNORE INTO sessions (date, plain_notes)
                    VALUES (?, ?)
                ''', (date, content))
                conn.commit()
                print(f"  ✓ Importiert: {date}")
            except Exception as e:
                print(f"  ! Fehler bei {date}: {e}")

if __name__ == "__main__":
    import_sessions()

