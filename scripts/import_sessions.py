import os
import glob
from db_manager import DatabaseManager

def import_sessions():
    db = DatabaseManager()
    # Pfad zu deinen Notizen
    notes_dir = "notes" 
    note_files = glob.glob(os.path.join(notes_dir, "*.md"))
    
    if not note_files:
        print(f"Keine .md Dateien in {notes_dir} gefunden.")
        return

    print(f"Importiere {len(note_files)} Sitzungen...")

    for file_path in note_files:
        # Dateiname ohne Pfad und ohne .md
        date = os.path.basename(file_path).replace(".md", "")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # INSERT OR IGNORE verhindert Duplikate, falls du das Skript mehrfach laufen lässt
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

