import os
import re
import sqlite3
import unicodedata

from lib.logging import get_logger

logger = get_logger("db")

class DatabaseManager:
    def __init__(self, db_path="data/campaign.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _row_to_dict(self, row):
        """Konvertiert sqlite3.Row zu echtem dict."""
        if row is None:
            return None
        try:
            return dict(row)
        except (TypeError, ValueError):
            return row


    def init_db(self):
        with self.get_connection() as conn:
            # WICHTIG: Foreign Key Support in SQLite muss explizit aktiviert werden
            conn.execute("PRAGMA foreign_keys = ON;")
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS characters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE, slug TEXT UNIQUE, type TEXT, player_name TEXT,
                    clan TEXT, affiliation TEXT, contact TEXT, status TEXT, notes TEXT,
                    biography TEXT, image_path TEXT, aliases TEXT, friends_raw TEXT,
                    foes_raw TEXT, location TEXT DEFAULT NULL, cause_of_death TEXT DEFAULT NULL
                )
            ''')

            # ON DELETE CASCADE sorgt dafür, dass Bilder gelöscht werden, wenn der Char weg ist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS character_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character_id INTEGER,
                    image_path TEXT,
                    FOREIGN KEY(character_id) REFERENCES characters(id) ON DELETE CASCADE
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE, ingame_date TEXT, title TEXT,
                    plain_notes TEXT, narrative TEXT, summary TEXT
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    description TEXT, status TEXT DEFAULT 'Open',
                    session_id INTEGER,
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS character_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character_id INTEGER, session_id INTEGER, log_entry TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(character_id) REFERENCES characters(id) ON DELETE CASCADE,
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS session_npcs (
                    session_id INTEGER, character_id INTEGER,
                    PRIMARY KEY(session_id, character_id),
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                    FOREIGN KEY(character_id) REFERENCES characters(id) ON DELETE CASCADE
                )
            ''')
            conn.commit()


    def add_character(self, name, slug, char_type="NPC", **kwargs):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Wir suchen jetzt primär über den Slug, da der einzigartig sein soll
            cursor.execute("SELECT * FROM characters WHERE slug = ? COLLATE NOCASE", (slug,))
            existing_char = cursor.fetchone()
            existing_dict = self._row_to_dict(existing_char)

            values = {
                "name": name,
                "slug": slug,
                "type": char_type,
                "player_name": kwargs.get("player_name", existing_dict.get("player_name", "") if existing_dict else ""),
                "clan": kwargs.get("clan", existing_dict.get("clan", "") if existing_dict else ""),
                "affiliation": kwargs.get("affiliation", existing_dict.get("affiliation", "") if existing_dict else ""),
                "contact": kwargs.get("contact", existing_dict.get("contact", "") if existing_dict else ""),
                "status": kwargs.get("status", existing_dict.get("status", "") if existing_dict else ""),
                "notes": kwargs.get("notes", existing_dict.get("notes", "") if existing_dict else ""),
                "biography": kwargs.get("biography", existing_dict.get("biography", "") if existing_dict else ""),
                "image_path": kwargs.get("image_path", existing_dict.get("image_path", "") if existing_dict else ""),
                "aliases": kwargs.get("aliases", existing_dict.get("aliases", "") if existing_dict else ""),
                "friends_raw": kwargs.get("friends_raw", existing_dict.get("friends_raw", "") if existing_dict else ""),
                "foes_raw": kwargs.get("foes_raw", existing_dict.get("foes_raw", "") if existing_dict else ""),
                "location": kwargs.get("location", existing_dict.get("location") if existing_dict else None),
                "cause_of_death": kwargs.get("cause_of_death", existing_dict.get("cause_of_death") if existing_dict else None),
            }

            if existing_dict:
                update_query = '''
                    UPDATE characters SET
                    name=?, type=?, player_name=?, clan=?, affiliation=?, contact=?,
                    status=?, notes=?, biography=?, image_path=?, aliases=?, friends_raw=?, foes_raw=?,
                    location=?, cause_of_death=?
                    WHERE slug=?
                '''
                params = (
                    values["name"], values["type"], values["player_name"], values["clan"],
                    values["affiliation"], values["contact"], values["status"], values["notes"],
                    values["biography"], values["image_path"], values["aliases"],
                    values["friends_raw"], values["foes_raw"],
                    values["location"], values["cause_of_death"],
                    slug
                )
                cursor.execute(update_query, params)
                char_id = existing_dict["id"]
            else:
                insert_query = '''
                    INSERT INTO characters
                    (name, slug, type, player_name, clan, affiliation, contact, status, notes, biography, image_path, aliases, friends_raw, foes_raw, location, cause_of_death)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''
                params = (
                    values["name"], values["slug"], values["type"], values["player_name"],
                    values["clan"], values["affiliation"], values["contact"], values["status"],
                    values["notes"], values["biography"], values["image_path"], values["aliases"],
                    values["friends_raw"], values["foes_raw"],
                    values["location"], values["cause_of_death"]
                )
                cursor.execute(insert_query, params)
                char_id = cursor.lastrowid

            conn.commit()
            return char_id

    def set_character_images(self, character_id, image_paths):
        """
        Setzt die Bilder für einen Character - ersetzt alte Bilder.
        Verhindert Duplikate.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Alte Bilder löschen
            cursor.execute(
                "DELETE FROM character_images WHERE character_id = ?",
                (character_id,)
            )

            # Neue Bilder hinzufügen
            for image_path in image_paths:
                cursor.execute(
                    "INSERT INTO character_images (character_id, image_path) VALUES (?, ?)",
                    (character_id, image_path)
                )

            conn.commit()

    def add_character_image(self, character_id, image_path):
        """
        Fügt ein Bild hinzu - verhindert aber Duplikate.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT id FROM character_images WHERE character_id = ? AND image_path = ?",
                (character_id, image_path)
            )

            if cursor.fetchone():
                return

            cursor.execute(
                "INSERT INTO character_images (character_id, image_path) VALUES (?, ?)",
                (character_id, image_path)
            )
            conn.commit()

    def get_all_characters(self, char_type=None):
        """Gibt alle Charaktere als echte Dictionaries zurück."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if char_type:
                cursor.execute("SELECT * FROM characters WHERE type = ? ORDER BY name", (char_type,))
            else:
                cursor.execute("SELECT * FROM characters ORDER BY name")

            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_character_by_slug(self, slug):
        """Gibt einen Charakter als echtes Dictionary zurück."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM characters WHERE slug = ? COLLATE NOCASE", (slug,))
            row = cursor.fetchone()
            return self._row_to_dict(row)

    def get_latest_session(self):
        """Holt den neuesten Session-Eintrag."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM sessions ORDER BY date DESC LIMIT 1"
            )
            row = cursor.fetchone()
            return self._row_to_dict(row)

    def get_all_sessions(self, limit=2, offset=0):
        """Holt alle Sessions mit Pagination."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM sessions ORDER BY date DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_all_sessions_raw(self):
        """Gibt alle Sessions als Liste von Dictionaries zurück."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions")
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_sessions_count(self):
        """Gibt die Gesamtzahl der Sessions zurück."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM sessions")
            row = cursor.fetchone()
            return row["count"] if row else 0

    def get_character_by_id(self, char_id):
        """Holt Character nach ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM characters WHERE id = ?", (char_id,))
            row = cursor.fetchone()
            return self._row_to_dict(row)

    def get_character_images(self, character_id):
        """Holt alle Bilder für einen Character."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT image_path FROM character_images WHERE character_id = ? ORDER BY id",
                (character_id,)
            )
            return [row["image_path"] for row in cursor.fetchall()]


    def insert_session(self, date: str, plain_notes: str, ingame_date: str = None, title: str = None):
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO sessions (date, plain_notes, ingame_date, title) VALUES (?, ?, ?, ?)",
                (date, plain_notes, ingame_date, title)
            )
            conn.commit()
    def get_session_by_date(self, date):
       with self.get_connection() as conn:
           cursor = conn.cursor()
           cursor.execute("SELECT * FROM sessions WHERE date = ?", (date,))
           return self._row_to_dict(cursor.fetchone())

    def update_session_ai_content(self, date, title, narrative, summary):
       with self.get_connection() as conn:
           conn.execute("UPDATE sessions SET title = ?, narrative = ?, summary = ? WHERE date = ?", 
                        (title, narrative, summary, date))
           conn.commit()


    def delete_record(self, table: str, record_id: int):
        """
        Deletes a record by ID from any table.
        Due to 'ON DELETE CASCADE' in the schema, dependent rows
        in other tables will be deleted automatically by SQLite.
        """
        # Wir validieren den Tabellennamen gegen eine Liste, um SQL-Injection zu verhindern
        allowed_tables = ['characters', 'sessions', 'tasks', 'character_logs']
        if table not in allowed_tables:
            raise ValueError(f"Table {table} is not allowed for deletion.")

        with self.get_connection() as conn:
            conn.execute(f"DELETE FROM {table} WHERE id = ?", (record_id,))
            conn.commit()
            logger.info(f"Deleted record {record_id} from {table}")
