import os
import sqlite3

from lib.log_utils import get_logger

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

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS character_relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_character_id INTEGER,
                    target_character_id INTEGER,
                    relation_type TEXT,
                    reason TEXT,
                    FOREIGN KEY(source_character_id) REFERENCES characters(id) ON DELETE CASCADE,
                    FOREIGN KEY(target_character_id) REFERENCES characters(id) ON DELETE CASCADE
                )
            ''')

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
                    description TEXT,
                    status TEXT DEFAULT 'Active',
                    session_id INTEGER,
                    reason TEXT DEFAULT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS character_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_character_id INTEGER,
                    target_character_id INTEGER DEFAULT NULL,
                    session_id INTEGER,
                    ingame_date TEXT,
                    change_description TEXT,
                    reasons TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(source_character_id) REFERENCES characters(id) ON DELETE CASCADE,
                    FOREIGN KEY(target_character_id) REFERENCES characters(id) ON DELETE CASCADE,
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

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS character_aliases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character_id INTEGER,
                    alias TEXT,
                    FOREIGN KEY(character_id) REFERENCES characters(id) ON DELETE CASCADE
                )
            ''')
            conn.commit()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    slug TEXT UNIQUE,
                    aliases TEXT
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS location_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    location_id INTEGER,
                    ingame_date TEXT,
                    description TEXT,
                    FOREIGN KEY(location_id) REFERENCES locations(id) ON DELETE CASCADE
                )
            ''')
            conn.commit()

    def add_character(self, name, slug, char_type="NPC", aliases=None, **kwargs):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Wir suchen jetzt primär über den Slug, da der einzigartig sein soll
            cursor.execute("SELECT * FROM characters WHERE slug = ? COLLATE NOCASE", (slug,))
            existing_char = cursor.fetchone()
            existing_dict = self._row_to_dict(existing_char)

            # Prepare the alias string for the legacy column
            alias_list = aliases if isinstance(aliases, list) else ([a.strip() for a in aliases.split(",")] if aliases else [])
            alias_string = ",".join(alias_list)

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
                "aliases": alias_string,
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

            # Sync character_aliases table
            cursor.execute("DELETE FROM character_aliases WHERE character_id = ?", (char_id,))
            for alias in alias_list:
                cursor.execute("INSERT INTO character_aliases (character_id, alias) VALUES (?, ?)", (char_id, alias))

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

    def get_open_tasks_by_session(self, session_id):
        """Holt alle offenen Tasks einer spezifischen Sitzung."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT description FROM tasks WHERE session_id = ? AND status = 'Open'", (session_id,))
            return [row["description"] for row in cursor.fetchall()]

    def get_previous_session(self, current_date):
        """Holt die chronologisch letzte Sitzung vor dem aktuellen Datum."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM sessions WHERE date < ? ORDER BY date DESC LIMIT 1",
                (current_date,)
            )
            return self._row_to_dict(cursor.fetchone())

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

    def get_recent_sessions(self, limit=2):
        """Holt die letzten N Sitzungen, sortiert von alt nach neu."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM (SELECT * FROM sessions ORDER BY date DESC LIMIT ?) ORDER BY date ASC",
                (limit,)
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]


    def get_npc_list_for_prompt(self):
        """
        Bereitet eine Liste für den LLM-Prompt vor.
        Die Aliase werden als kommaseparierter String übergeben,
        was dem LLM die Zuordnung zu den Slugs erleichtert.
        """
        chars = self.get_all_characters()
        npc_list = []
        for char in chars:
            npc_list.append(
                f"Name: {char['name']} | Slug: {char['slug']} | Aliases: [{char['aliases']}]"
            )
        return "\n".join(npc_list)
  
    def add_task(self, session_id, description, status="Open"):
        with self.get_connection() as conn:
            conn.execute("INSERT INTO tasks (session_id, description, status) VALUES (?, ?, ?)",
                         (session_id, description, status))
            conn.commit()

    def update_npc_from_ai(self, character_slug, status, log_entry, session_id, biography_addition=None):
        """
        Updates NPC status, adds a log entry to history, and appends to biography if new info is provided.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            char = self.get_character_by_slug(character_slug)
            if not char:
                return False

            # Update current status
            cursor.execute("UPDATE characters SET status = ? WHERE id = ?", (status, char["id"]))

            # Record the event in the character's history log
            cursor.execute("INSERT INTO character_logs (character_id, session_id, log_entry) VALUES (?, ?, ?)",
                           (char["id"], session_id, log_entry))

            # Append new info to biography if provided
            if biography_addition:
                old_bio = char["biography"] or ""
                new_bio = f"{old_bio}\n\n{biography_addition}".strip()
                cursor.execute("UPDATE characters SET biography = ? WHERE id = ?", (new_bio, char["id"]))

            conn.commit()
            return True

    def update_session_ai_content(self, date, title, ingame_date, narrative, summary):
        """
        Updates the session content with the AI-generated output.
        """
        with self.get_connection() as conn:
            conn.execute("UPDATE sessions SET title = ?, ingame_date = ?, narrative = ?, summary = ? WHERE date = ?",
                         (title, ingame_date, narrative, summary, date))
            conn.commit()

    def update_npc_relationship(self, source_slug, target_slug, relation_type, reason, session_id):
        """
        Updates the relationship between two NPCs in the database,
        storing the type and the reason for the change.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            source = self.get_character_by_slug(source_slug)
            target = self.get_character_by_slug(target_slug)

            if not source or not target:
                logger.warning(f"Relationship update failed: {source_slug} or {target_slug} not found.")
                return False

            # Remove old relationship record to ensure only the latest state is stored
            cursor.execute("DELETE FROM character_relationships WHERE source_character_id = ? AND target_character_id = ?",
                           (source["id"], target["id"]))

            # Insert the new relationship state with the reason
            cursor.execute("INSERT INTO character_relationships (source_character_id, target_character_id, relation_type, reason) VALUES (?, ?, ?, ?)",
                           (source["id"], target["id"], relation_type, reason))

            # Also log the change in the character's history for long-term tracking
            log_msg = f"Relationship with {target['name']} updated to {relation_type}. Reason: {reason}"
            cursor.execute("INSERT INTO character_logs (character_id, session_id, log_entry) VALUES (?, ?, ?)",
                           (source["id"], session_id, log_msg))

            conn.commit()
            return True

    def get_all_active_tasks(self):
        """Holt alle aktiven Tasks inklusive ihrer ID für das LLM-Referenzing."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, description, status FROM tasks WHERE status != 'Accomplished'")
            return [dict(row) for row in cursor.fetchall()]

    def sync_task(self, session_id, description, status, reason=None, task_id=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            existing_id = None
            existing_reason = ""

            if task_id:
                cursor.execute("SELECT id, reason FROM tasks WHERE id = ?", (task_id,))
            else:
                cursor.execute("SELECT id, reason FROM tasks WHERE description = ? AND session_id = ?", (description, session_id))

            row = cursor.fetchone()

            if row:
                existing_id = row['id']
                existing_reason = row['reason'] or ""

                new_reason = f"{existing_reason} | {reason}".strip(" | ") if reason else existing_reason

                cursor.execute("UPDATE tasks SET status = ?, reason = ? WHERE id = ?",
                               (status, new_reason, existing_id))
            else:
                cursor.execute("INSERT INTO tasks (session_id, description, status, reason) VALUES (?, ?, ?, ?)",
                               (session_id, description, status, reason or "Erstellt."))

            conn.commit()

    def add_alias_to_character(self, character_slug, new_alias):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            char = self.get_character_by_slug(character_slug)
            if not char:
                return False

            # 1. Aktuelle Aliase als Set holen (verhindert Duplikate sofort)
            # Wir holen sie aus der character_aliases Tabelle für absolute Sicherheit
            cursor.execute("SELECT alias FROM character_aliases WHERE character_id = ?", (char['id'],))
            current_aliases = {row['alias'] for row in cursor.fetchall()}

            # 2. Prüfen, ob der neue Alias schon dabei ist
            if new_alias not in current_aliases:
                # 3. Insert in die relationale Tabelle
                cursor.execute("INSERT INTO character_aliases (character_id, alias) VALUES (?, ?)",
                               (char['id'], new_alias))

                # 4. Update des Legacy-Strings in der characters Tabelle
                # Wir aktualisieren den String basierend auf dem vollständigen Set
                current_aliases.add(new_alias)
                alias_string = ",".join(list(current_aliases))

                cursor.execute("UPDATE characters SET aliases = ? WHERE id = ?",
                               (alias_string, char['id']))

                conn.commit()
                logger.info(f"Added new alias '{new_alias}' for {character_slug}")
                return True

            return False

    def log_character_interaction(self, source_id, target_id, ingame_date, change_desc, reason):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Prüfen, ob für diese Interaktion am gleichen Tag schon ein Log existiert
            cursor.execute('''
                SELECT id, reasons FROM character_logs
                WHERE source_character_id = ? AND target_character_id = ?
                AND ingame_date = ? AND change_description = ?
            ''', (source_id, target_id, ingame_date, change_desc))

            row = cursor.fetchone()

            if row:
                # Bestehende Reasons als Liste laden
                reasons = json.loads(row['reasons']) if row['reasons'] else []
                if reason not in reasons:
                    reasons.append(reason)
                cursor.execute("UPDATE character_logs SET reasons = ? WHERE id = ?",
                               (json.dumps(reasons), row['id']))
            else:
                # Neuen Log-Eintrag erstellen
                cursor.execute('''
                    INSERT INTO character_logs
                    (source_character_id, target_character_id, ingame_date, change_description, reasons)
                    VALUES (?, ?, ?, ?, ?)
                ''', (source_id, target_id, ingame_date, change_desc, json.dumps([reason])))

            conn.commit()

    def get_logs_for_character_relation(self, source_id, target_id):
        """Holt alle Log-Einträge zwischen zwei Charakteren."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT ingame_date, change_description, reasons
                FROM character_logs
                WHERE source_character_id = ? AND target_character_id = ?
                ORDER BY ingame_date ASC
            ''', (source_id, target_id))

            results = []
            for row in cursor.fetchall():
                results.append({
                    "date": row['ingame_date'],
                    "change": row['change_description'],
                    "reasons": json.loads(row['reasons'])
                })
            return results


    def update_character_from_ai_data(self, slug, **kwargs):
        """Update character fields dynamically based on LLM output."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Nur erlaubte Spalten updaten
            allowed = ['status', 'contact', 'friends_raw', 'foes_raw', 'cause_of_death', 'biography']
            fields = [f"{k} = ?" for k in kwargs if k in allowed]
            params = [kwargs[k] for k in kwargs if k in allowed]

            if not fields:
                return False

            params.append(slug)
            cursor.execute(f"UPDATE characters SET {', '.join(fields)} WHERE slug = ?", params)
            conn.commit()
            return True

    def log_location_update(self, location_slug, ingame_date, description):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM locations WHERE slug = ?", (location_slug,))
            row = cursor.fetchone()
            if row:
                loc_id = row['id']
                cursor.execute('''
                    INSERT INTO location_history (location_id, ingame_date, description)
                    VALUES (?, ?, ?)
                ''', (loc_id, ingame_date, description))
                conn.commit()

    def get_location_list_for_prompt(self):
        """
        Bereitet eine Liste aller Orte für den LLM-Prompt vor.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, slug, aliases FROM locations")
            rows = cursor.fetchall()

            # Formatieren als Textblock für das LLM
            loc_list = []
            for row in rows:
                loc_list.append(
                    f"Name: {row['name']} | Slug: {row['slug']} | Aliases: [{row['aliases']}]"
                )
            return "\n".join(loc_list)

