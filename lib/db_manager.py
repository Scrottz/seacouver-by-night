import json
import os
import sqlite3
from typing import Optional, Union
from lib.log_utils import get_logger

logger = get_logger("db")


class DatabaseManager:
    def __init__(self, db_path="data/campaign.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_db()

    def get_connection(self):
        """Establishes a connection to the SQLite database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Allows accessing columns by name
        return conn

    def _row_to_dict(self, row):
        """Converts an sqlite3.Row object to a real dictionary."""
        if row is None:
            return None
        try:
            return dict(row)
        except (TypeError, ValueError):
            return row

    def init_db(self):
        """Initializes the database schema by creating tables if they don't exist."""
        with self.get_connection() as conn:
            conn.execute(
                "PRAGMA foreign_keys = ON;"
            )  # Ensure foreign key constraints are enforced
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS characters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE, slug TEXT UNIQUE, type TEXT, player_name TEXT,
                    clan TEXT, affiliation TEXT, contact TEXT, status TEXT, notes TEXT,
                    biography TEXT, image_path TEXT, aliases TEXT, friends_raw TEXT,
                    foes_raw TEXT, location TEXT DEFAULT NULL, cause_of_death TEXT DEFAULT NULL
                )
            """)

            # Corrected character_relationships table definition: 'reason' will store JSON string
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS character_relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_character_id INTEGER NOT NULL,
                    target_character_id INTEGER NOT NULL,
                    relation_type TEXT NOT NULL, -- e.g., 'friend', 'foe', 'neutral'
                    reason TEXT, -- Stored as a JSON array of reasons, can be NULL initially
                    FOREIGN KEY(source_character_id) REFERENCES characters(id) ON DELETE CASCADE,
                    FOREIGN KEY(target_character_id) REFERENCES characters(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS character_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character_id INTEGER,
                    image_path TEXT,
                    FOREIGN KEY(character_id) REFERENCES characters(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE, ingame_date TEXT, title TEXT,
                    plain_notes TEXT, narrative TEXT, summary TEXT
                )
            """)

            # tasks table: reason now expected to be JSON string
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    description TEXT,
                    status TEXT DEFAULT 'Active',
                    session_id INTEGER,
                    reason TEXT DEFAULT '[]', -- Default to an empty JSON array string
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            """)

            # Corrected character_logs table definition with NOT NULL constraints
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS character_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_character_id INTEGER NOT NULL,
                    target_character_id INTEGER DEFAULT NULL,
                    session_id INTEGER NOT NULL,
                    ingame_date TEXT NOT NULL,
                    change_description TEXT NOT NULL,
                    reasons TEXT, -- Stored as JSON string
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(source_character_id) REFERENCES characters(id) ON DELETE CASCADE,
                    FOREIGN KEY(target_character_id) REFERENCES characters(id) ON DELETE CASCADE,
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_npcs (
                    session_id INTEGER, character_id INTEGER,
                    PRIMARY KEY(session_id, character_id),
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                    FOREIGN KEY(character_id) REFERENCES characters(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS character_aliases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character_id INTEGER,
                    alias TEXT,
                    FOREIGN KEY(character_id) REFERENCES characters(id) ON DELETE CASCADE
                )
            """)
            conn.commit()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    slug TEXT UNIQUE,
                    aliases TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS location_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    location_id INTEGER,
                    ingame_date TEXT,
                    description TEXT,
                    FOREIGN KEY(location_id) REFERENCES locations(id) ON DELETE CASCADE
                )
            """)
            conn.commit()

    def add_character(
        self,
        name,
        slug,
        char_type="NPC",
        aliases: Optional[Union[str, list[str]]] = None,
        **kwargs,
    ):
        """
        Adds a new character or updates an existing one based on slug.
        Includes handling for legacy 'aliases' string column and syncing with 'character_aliases' table.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Search primarily by slug, as it should be unique
            cursor.execute(
                "SELECT * FROM characters WHERE slug = ? COLLATE NOCASE", (slug,)
            )
            existing_char = cursor.fetchone()
            existing_dict = self._row_to_dict(existing_char)

            # Prepare the alias string for the legacy column
            alias_list = (
                aliases
                if isinstance(aliases, list)
                else ([a.strip() for a in aliases.split(",")] if aliases else [])
            )
            alias_string = ",".join(alias_list)

            values = {
                "name": name,
                "slug": slug,
                "type": char_type,
                "player_name": kwargs.get(
                    "player_name",
                    existing_dict.get("player_name", "") if existing_dict else "",
                ),
                "clan": kwargs.get(
                    "clan", existing_dict.get("clan", "") if existing_dict else ""
                ),
                "affiliation": kwargs.get(
                    "affiliation",
                    existing_dict.get("affiliation", "") if existing_dict else "",
                ),
                "contact": kwargs.get(
                    "contact", existing_dict.get("contact", "") if existing_dict else ""
                ),
                "status": kwargs.get(
                    "status", existing_dict.get("status", "") if existing_dict else ""
                ),
                "notes": kwargs.get(
                    "notes", existing_dict.get("notes", "") if existing_dict else ""
                ),
                "biography": kwargs.get(
                    "biography",
                    existing_dict.get("biography", "") if existing_dict else "",
                ),
                "image_path": kwargs.get(
                    "image_path",
                    existing_dict.get("image_path", "") if existing_dict else "",
                ),
                "aliases": alias_string,
                "friends_raw": kwargs.get(
                    "friends_raw",
                    existing_dict.get("friends_raw", "") if existing_dict else "",
                ),
                "foes_raw": kwargs.get(
                    "foes_raw",
                    existing_dict.get("foes_raw", "") if existing_dict else "",
                ),
                "location": kwargs.get(
                    "location", existing_dict.get("location") if existing_dict else None
                ),
                "cause_of_death": kwargs.get(
                    "cause_of_death",
                    existing_dict.get("cause_of_death") if existing_dict else None,
                ),
            }

            if existing_dict:
                update_query = """
                    UPDATE characters SET
                    name=?, type=?, player_name=?, clan=?, affiliation=?, contact=?,
                    status=?, notes=?, biography=?, image_path=?, aliases=?, friends_raw=?, foes_raw=?,
                    location=?, cause_of_death=?
                    WHERE slug=?
                """
                params = (
                    values["name"],
                    values["type"],
                    values["player_name"],
                    values["clan"],
                    values["affiliation"],
                    values["contact"],
                    values["status"],
                    values["notes"],
                    values["biography"],
                    values["image_path"],
                    values["aliases"],
                    values["friends_raw"],
                    values["foes_raw"],
                    values["location"],
                    values["cause_of_death"],
                    slug,
                )
                cursor.execute(update_query, params)
                char_id = existing_dict["id"]
            else:
                insert_query = """
                    INSERT INTO characters
                    (name, slug, type, player_name, clan, affiliation, contact, status, notes, biography, image_path, aliases, friends_raw, foes_raw, location, cause_of_death)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    values["name"],
                    values["slug"],
                    values["type"],
                    values["player_name"],
                    values["clan"],
                    values["affiliation"],
                    values["contact"],
                    values["status"],
                    values["notes"],
                    values["biography"],
                    values["image_path"],
                    values["aliases"],
                    values["friends_raw"],
                    values["foes_raw"],
                    values["location"],
                    values["cause_of_death"],
                )
                cursor.execute(insert_query, params)
                char_id = cursor.lastrowid

            # Sync character_aliases table
            cursor.execute(
                "DELETE FROM character_aliases WHERE character_id = ?", (char_id,)
            )
            for alias in alias_list:
                cursor.execute(
                    "INSERT INTO character_aliases (character_id, alias) VALUES (?, ?)",
                    (char_id, alias),
                )

            conn.commit()
            return char_id

    def set_character_images(self, character_id: int, image_paths: list[str]):
        """
        Sets the images for a character - replaces old images.
        Prevents duplicates.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Delete old images
            cursor.execute(
                "DELETE FROM character_images WHERE character_id = ?", (character_id,)
            )

            # Add new images
            for image_path in image_paths:
                cursor.execute(
                    "INSERT INTO character_images (character_id, image_path) VALUES (?, ?)",
                    (character_id, image_path),
                )

            conn.commit()

    def add_character_image(self, character_id: int, image_path: str):
        """
        Adds an image, but prevents duplicates.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT id FROM character_images WHERE character_id = ? AND image_path = ?",
                (character_id, image_path),
            )

            if cursor.fetchone():
                return

            cursor.execute(
                "INSERT INTO character_images (character_id, image_path) VALUES (?, ?)",
                (character_id, image_path),
            )
            conn.commit()

    def get_all_characters(self, char_type: Optional[str] = None):
        """Returns all characters as real dictionaries."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if char_type:
                cursor.execute(
                    "SELECT * FROM characters WHERE type = ? ORDER BY name",
                    (char_type,),
                )
            else:
                cursor.execute("SELECT * FROM characters ORDER BY name")

            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_character_by_slug(self, slug: str):
        """Returns a character as a real dictionary based on its slug."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM characters WHERE slug = ? COLLATE NOCASE", (slug,)
            )
            row = cursor.fetchone()
            return self._row_to_dict(row)

    def get_latest_session(self):
        """Fetches the latest session entry."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions ORDER BY date DESC LIMIT 1")
            row = cursor.fetchone()
            return self._row_to_dict(row)

    def get_session_date_from_id(self, session_id: int):
        """Fetches the real date of a session by its ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT date FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            return row["date"] if row else None

    def get_session_ingame_date_from_id(self, session_id: int):
        """Fetches the in-game date of a session by its ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT ingame_date FROM sessions WHERE id = ?", (session_id,)
            )
            row = cursor.fetchone()
            return row["ingame_date"] if row else None

    def get_all_sessions(self, limit: int = 2, offset: int = 0):
        """Fetches all sessions with pagination."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM sessions ORDER BY date DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_all_sessions_raw(self):
        """Returns all sessions as a list of dictionaries."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions")
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_sessions_count(self):
        """Returns the total number of sessions."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM sessions")
            row = cursor.fetchone()
            return row["count"] if row else 0

    def get_character_by_id(self, char_id: int):
        """Fetches a character by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM characters WHERE id = ?", (char_id,))
            row = cursor.fetchone()
            return self._row_to_dict(row)

    def get_character_images(self, character_id: int):
        """Fetches all images for a character."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT image_path FROM character_images WHERE character_id = ? ORDER BY id",
                (character_id,),
            )
            return [row["image_path"] for row in cursor.fetchall()]

    def insert_session(
        self,
        date: str,
        plain_notes: str,
        ingame_date: Optional[str] = None,
        title: Optional[str] = None,
    ):
        """Inserts a new session into the database."""
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO sessions (date, plain_notes, ingame_date, title) VALUES (?, ?, ?, ?)",
                (date, plain_notes, ingame_date, title),
            )
            conn.commit()

    def get_session_by_date(self, date: str):
        """Fetches a session by its real date."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE date = ?", (date,))
            return self._row_to_dict(cursor.fetchone())

    def get_open_tasks_by_session(self, session_id: int):
        """Fetches all open tasks for a specific session."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT description FROM tasks WHERE session_id = ? AND status = 'Open'",
                (session_id,),
            )
            return [row["description"] for row in cursor.fetchall()]

    def get_previous_session(self, current_date: str):
        """Fetches the chronologically last session before the current date."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM sessions WHERE date < ? ORDER BY date DESC LIMIT 1",
                (current_date,),
            )
            return self._row_to_dict(cursor.fetchone())

    def delete_record(self, table: str, record_id: int):
        """
        Deletes a record by ID from any table.
        Due to 'ON DELETE CASCADE' in the schema, dependent rows
        in other tables will be deleted automatically by SQLite.
        """
        # Validate the table name against a whitelist to prevent SQL injection
        allowed_tables = [
            "characters",
            "sessions",
            "tasks",
            "character_logs",
            "locations",
            "character_relationships",
            "character_images",
            "session_npcs",
            "character_aliases",
            "location_history",
        ]
        if table not in allowed_tables:
            raise ValueError(f"Table {table} is not allowed for deletion.")

        with self.get_connection() as conn:
            conn.execute(f"DELETE FROM {table} WHERE id = ?", (record_id,))
            conn.commit()
            logger.info(f"Deleted record {record_id} from {table}")

    def get_recent_sessions(self, limit: int = 2):
        """Fetches the last N sessions, sorted from oldest to newest."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM (SELECT * FROM sessions ORDER BY date DESC LIMIT ?) ORDER BY date ASC",
                (limit,),
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_npc_list_for_prompt(self):
        """
        Prepares a list of all NPCs for the LLM prompt.
        Aliases are passed as a comma-separated string to facilitate LLM mapping to slugs.
        """
        chars = self.get_all_characters()
        npc_list = []
        for char in chars:
            npc_list.append(
                f"Name: {char['name']} | Slug: {char['slug']} | Aliases: [{char['aliases']}]"
            )
        return "\n".join(npc_list)

    def add_task(self, session_id: int, description: str, status: str = "Open"):
        """Adds a new task associated with a session."""
        with self.get_connection() as conn:
            # When adding a new task, initialize 'reason' as an empty JSON array
            conn.execute(
                "INSERT INTO tasks (session_id, description, status, reason) VALUES (?, ?, ?, ?)",
                (session_id, description, status, json.dumps([])),
            )
            conn.commit()

    def update_npc_from_ai(
        self,
        character_slug: str,
        status: str,
        log_entry: str,
        session_id: int,
        biography_addition: Optional[str] = None,
    ):
        """
        Updates NPC status, adds a log entry to history, and appends to biography if new info is provided.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            char = self.get_character_by_slug(character_slug)
            if not char:
                logger.warning(
                    f"Character with slug '{character_slug}' not found for AI update."
                )
                return False

            # Update current status
            cursor.execute(
                "UPDATE characters SET status = ? WHERE id = ?", (status, char["id"])
            )

            # Get the in-game date for the session
            ingame_date = self.get_session_ingame_date_from_id(session_id)
            if not ingame_date:
                logger.warning(
                    f"Could not find ingame_date for session_id {session_id}. Using 'Unknown Date'."
                )
                ingame_date = "Unknown Date"

            # Record the event in the character's history log
            cursor.execute(
                "INSERT INTO character_logs (source_character_id, target_character_id, session_id, ingame_date, change_description, reasons) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    char["id"],
                    None,
                    session_id,
                    ingame_date,
                    log_entry,
                    json.dumps([log_entry]),
                ),
            )

            # Append new info to biography if provided
            if biography_addition:
                old_bio = char["biography"] or ""
                new_bio = f"{old_bio}\n\n{biography_addition}".strip()
                cursor.execute(
                    "UPDATE characters SET biography = ? WHERE id = ?",
                    (new_bio, char["id"]),
                )

            conn.commit()
            return True

    def update_session_ai_content(
        self, date: str, title: str, ingame_date: str, narrative: str, summary: str
    ):
        """
        Updates the session content with the AI-generated output.
        """
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET title = ?, ingame_date = ?, narrative = ?, summary = ? WHERE date = ?",
                (title, ingame_date, narrative, summary, date),
            )
            conn.commit()
            logger.info(f"Updated session '{date}' with AI content.")

    def _get_character_relationship(self, source_id: int, target_id: int):
        """
        Helper method to retrieve an existing character relationship.
        Returns the relationship as a dictionary or None if not found.
        Parses the 'reason' field from JSON string to a list.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, source_character_id, target_character_id, relation_type, reason FROM character_relationships WHERE source_character_id = ? AND target_character_id = ?",
                (source_id, target_id),
            )
            row = cursor.fetchone()
            if row:
                rel_dict = self._row_to_dict(row)
                if rel_dict["reason"]:
                    try:
                        rel_dict["reason"] = json.loads(
                            rel_dict["reason"]
                        )  # Convert JSON string back to list
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Invalid JSON in character_relationships reason for ID {rel_dict['id']}: {rel_dict['reason']}. Treating as single string list."
                        )
                        rel_dict["reason"] = [
                            rel_dict["reason"]
                        ]  # Fallback for old/malformed entries
                else:
                    rel_dict["reason"] = []
                return rel_dict
            return None

    def update_npc_relationship(
        self,
        source_slug: str,
        target_slug: str,
        new_relation_type: str,
        new_reason: str,
        session_id: int,
    ):
        """
        Updates the relationship between two NPCs in the database.
        - Enforces allowed relation types ('friend', 'foe', 'neutral').
        - Stores reasons as a JSON list, appending new reasons if the relation_type stays the same.
        - Overwrites the relation_type and starts a new reason list if the type changes.
        - Ensures only one active relationship entry exists between the two characters.
        - Also logs the change in the character_logs history.
        """
        allowed_relation_types = ["friend", "foe", "neutral"]
        if new_relation_type not in allowed_relation_types:
            logger.warning(
                f"Invalid relation type '{new_relation_type}' provided. Must be one of {allowed_relation_types}."
            )
            return False

        with self.get_connection() as conn:
            cursor = conn.cursor()
            source_char = self.get_character_by_slug(source_slug)
            target_char = self.get_character_by_slug(target_slug)

            if not source_char or not target_char:
                logger.warning(
                    f"Relationship update failed: source character '{source_slug}' or target character '{target_slug}' not found."
                )
                return False

            source_id = source_char["id"]
            target_id = target_char["id"]

            existing_relationship = self._get_character_relationship(
                source_id, target_id
            )
            reasons_to_store = []

            if existing_relationship:
                # If the relation type is the same, append to existing reasons
                if existing_relationship["relation_type"] == new_relation_type:
                    reasons_to_store = existing_relationship[
                        "reason"
                    ]  # Already a list from _get_character_relationship
                    if new_reason and new_reason not in reasons_to_store:
                        reasons_to_store.append(new_reason)
                    logger.info(
                        f"Appended reason '{new_reason}' to existing relationship for {source_slug} and {target_slug} as {new_relation_type}."
                    )
                else:
                    # If relation type changes, start a new list of reasons for the new type
                    reasons_to_store = [new_reason] if new_reason else []
                    logger.info(
                        f"Relationship type changed for {source_slug} and {target_slug} from {existing_relationship['relation_type']} to {new_relation_type}. Starting new reasons list with '{new_reason}'."
                    )

                # Delete the old relationship entry (to ensure only one active entry)
                cursor.execute(
                    "DELETE FROM character_relationships WHERE source_character_id = ? AND target_character_id = ?",
                    (source_id, target_id),
                )
            else:
                # If no existing relationship, start a new list of reasons
                reasons_to_store = [new_reason] if new_reason else []
                logger.info(
                    f"Creating new relationship for {source_slug} and {target_slug} as {new_relation_type} with reason '{new_reason}'."
                )

            # Insert the new/updated relationship state with the JSON reasons
            cursor.execute(
                "INSERT INTO character_relationships (source_character_id, target_character_id, relation_type, reason) VALUES (?, ?, ?, ?)",
                (source_id, target_id, new_relation_type, json.dumps(reasons_to_store)),
            )

            # Get the in-game date for the session for character_logs
            ingame_date = self.get_session_ingame_date_from_id(session_id)
            if not ingame_date:
                logger.warning(
                    f"Could not find ingame_date for session_id {session_id} for relationship log. Using 'Unknown Date'."
                )
                ingame_date = "Unknown Date"

            # Also log the change in the character's history for long-term tracking
            log_msg_desc = f"Relationship with {target_char['name']} changed to {new_relation_type}."
            # The 'reasons' for character_logs should still be a specific reason for *this event*,
            # not the accumulated history from character_relationships, to avoid redundancy in the event log.
            cursor.execute(
                "INSERT INTO character_logs (source_character_id, target_character_id, session_id, ingame_date, change_description, reasons) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    source_id,
                    target_id,
                    session_id,
                    ingame_date,
                    log_msg_desc,
                    json.dumps([new_reason] if new_reason else []),
                ),
            )

            conn.commit()
            return True

    def get_all_active_tasks(self):
        """Fetches all active tasks including their ID for LLM referencing."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, description, status, reason FROM tasks WHERE status != 'Accomplished'"
            )
            # Parse 'reason' from JSON string to list for the application layer
            tasks = []
            for row in cursor.fetchall():
                task_dict = self._row_to_dict(row)
                if task_dict["reason"]:
                    try:
                        task_dict["reason"] = json.loads(task_dict["reason"])
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Invalid JSON in task reason for ID {task_dict['id']}: {task_dict['reason']}. Treating as single string list."
                        )
                        task_dict["reason"] = [
                            task_dict["reason"]
                        ]  # Fallback for old/malformed entries
                else:
                    task_dict["reason"] = []
                tasks.append(task_dict)
            return tasks

    def sync_task(
        self,
        session_id: int,
        description: str,
        status: str,
        new_reason: Optional[str] = None,
        task_id: Optional[int] = None,
    ):
        """
        Syncs a task's status and reasons. If task_id is provided, it updates by ID.
        Otherwise, it attempts to find by description and session_id.
        If no existing task is found, a new one is inserted.
        'reason' is stored as a JSON list, with new_reason appended if not already present.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            existing_id = None
            current_reasons: list[str] = []  # Initialize as empty list

            if task_id:
                cursor.execute("SELECT id, reason FROM tasks WHERE id = ?", (task_id,))
            else:
                cursor.execute(
                    "SELECT id, reason FROM tasks WHERE description = ? AND session_id = ?",
                    (description, session_id),
                )

            row = cursor.fetchone()

            if row:
                existing_id = row["id"]
                # Load existing reasons from JSON string
                if row["reason"]:
                    try:
                        current_reasons = json.loads(row["reason"])
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Invalid JSON in task reason for ID {existing_id}: {row['reason']}. Treating as single string list."
                        )
                        # If parsing fails, assume it's an old string and put it in a list
                        current_reasons = [row["reason"]]

                # Add new reason if it's not empty and not already in the list
                if new_reason and new_reason not in current_reasons:
                    current_reasons.append(new_reason)

                # Update task with new status and JSON-dumped reasons
                cursor.execute(
                    "UPDATE tasks SET status = ?, reason = ? WHERE id = ?",
                    (status, json.dumps(current_reasons), existing_id),
                )
                logger.info(
                    f"Updated task ID {existing_id}: status '{status}', added reason '{new_reason}'."
                )
            else:
                # Insert new task. Initial reason is just the new_reason in a list.
                initial_reasons = [new_reason] if new_reason else []
                cursor.execute(
                    "INSERT INTO tasks (session_id, description, status, reason) VALUES (?, ?, ?, ?)",
                    (session_id, description, status, json.dumps(initial_reasons)),
                )
                logger.info(
                    f"Inserted new task for session {session_id}: '{description}' with initial reason '{new_reason}'."
                )

            conn.commit()

    def add_alias_to_character(self, character_slug: str, new_alias: str):
        """
        Adds a new alias to a character, preventing duplicates and updating the legacy aliases string.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            char = self.get_character_by_slug(character_slug)
            if not char:
                return False

            # 1. Fetch current aliases as a set (prevents immediate duplicates)
            # We fetch them from the character_aliases table for absolute certainty
            cursor.execute(
                "SELECT alias FROM character_aliases WHERE character_id = ?",
                (char["id"],),
            )
            current_aliases = {row["alias"] for row in cursor.fetchall()}

            # 2. Check if the new alias is already present
            if new_alias not in current_aliases:
                # 3. Insert into the relational table
                cursor.execute(
                    "INSERT INTO character_aliases (character_id, alias) VALUES (?, ?)",
                    (char["id"], new_alias),
                )

                # 4. Update the legacy string in the characters table
                # We update the string based on the complete set
                current_aliases.add(new_alias)
                alias_string = ",".join(list(current_aliases))

                cursor.execute(
                    "UPDATE characters SET aliases = ? WHERE id = ?",
                    (alias_string, char["id"]),
                )

                conn.commit()
                logger.info(f"Added new alias '{new_alias}' for {character_slug}")
                return True

            return False

    def log_character_interaction(
        self,
        source_id: int,
        target_id: Optional[int],
        ingame_date: str,
        change_desc: str,
        reason: str,
        session_id: int,
    ):
        """
        Logs a character interaction or updates an existing one if it occurred on the same day
        within the same session with the same source, target, and description. Reasons are added to a JSON array.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check if a log already exists for this interaction on the same day and session
            cursor.execute(
                """
                SELECT id, reasons FROM character_logs
                WHERE source_character_id = ? AND target_character_id = ?
                AND session_id = ?
                AND ingame_date = ? AND change_description = ?
            """,
                (source_id, target_id, session_id, ingame_date, change_desc),
            )

            row = cursor.fetchone()

            if row:
                # Load existing reasons as a list
                reasons = json.loads(row["reasons"]) if row["reasons"] else []
                if (
                    reason and reason not in reasons
                ):  # Only add if new reason and not already present
                    reasons.append(reason)
                cursor.execute(
                    "UPDATE character_logs SET reasons = ? WHERE id = ?",
                    (json.dumps(reasons), row["id"]),
                )
                logger.info(
                    f"Updated interaction log for source {source_id}, target {target_id} in session {session_id}. Added reason: '{reason}'."
                )
            else:
                # Create a new log entry
                reasons_for_log = (
                    [reason] if reason else []
                )  # Start with the current reason
                cursor.execute(
                    """
                    INSERT INTO character_logs
                    (source_character_id, target_character_id, session_id, ingame_date, change_description, reasons)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        source_id,
                        target_id,
                        session_id,
                        ingame_date,
                        change_desc,
                        json.dumps(reasons_for_log),
                    ),
                )
                logger.info(
                    f"New interaction log created for source {source_id}, target {target_id} in session {session_id}: '{change_desc}'."
                )

            conn.commit()

    def get_logs_for_character_relation(self, source_id: int, target_id: int):
        """Holt alle Log-Einträge zwischen zwei Charakteren."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT ingame_date, change_description, reasons
                FROM character_logs
                WHERE source_character_id = ? AND target_character_id = ?
                ORDER BY ingame_date ASC
            """,
                (source_id, target_id),
            )

            results = []
            for row in cursor.fetchall():
                results.append(
                    {
                        "date": row["ingame_date"],
                        "change": row["change_description"],
                        "reasons": json.loads(row["reasons"]) if row["reasons"] else [],
                    }
                )
            return results

    def update_character_from_ai_data(self, slug: str, **kwargs):
        """Update character fields dynamically based on LLM output."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Only update allowed columns
            allowed = [
                "status",
                "contact",
                "friends_raw",
                "foes_raw",
                "cause_of_death",
                "biography_addition",
            ]
            # We need to handle 'biography_addition' separately to append

            update_fields = []
            update_params = []
            biography_to_add = None

            for k, v in kwargs.items():
                if k == "biography_addition" and v is not None:
                    biography_to_add = v
                elif k in allowed and v is not None:
                    update_fields.append(f"{k} = ?")
                    update_params.append(v)

            if not update_fields and not biography_to_add:
                logger.info(
                    f"No allowed fields to update for character '{slug}' from AI data."
                )
                return False

            # Handle biography_addition separately if present
            if biography_to_add:
                char = self.get_character_by_slug(slug)
                if char:
                    old_bio = char.get("biography", "") or ""
                    new_bio = f"{old_bio}\n\n{biography_to_add}".strip()
                    update_fields.append("biography = ?")
                    update_params.append(new_bio)
                    logger.info(f"Appended to biography for character '{slug}'.")
                else:
                    logger.warning(
                        f"Character with slug '{slug}' not found for biography_addition. Skipping."
                    )

            if update_fields:  # Execute update only if there are fields to change
                update_params.append(slug)
                cursor.execute(
                    f"UPDATE characters SET {', '.join(update_fields)} WHERE slug = ?",
                    update_params,
                )
                conn.commit()
                logger.info(f"Character '{slug}' updated from AI data.")

            return True

    def add_location(
        self, name: str, slug: str, aliases: Optional[Union[str, list[str]]] = None
    ):
        """
        Adds a new location or updates an existing one if the slug already exists.
        Returns the ID of the location.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Ensure aliases is a comma-separated string for DB storage
            if isinstance(aliases, list):
                aliases_string = ",".join(aliases)
            elif aliases:
                aliases_string = aliases
            else:
                aliases_string = ""

            # Check if location with this slug already exists
            cursor.execute(
                "SELECT id, name, aliases FROM locations WHERE slug = ? COLLATE NOCASE",
                (slug,),
            )
            existing_loc_row = cursor.fetchone()
            existing_loc = (
                self._row_to_dict(existing_loc_row) if existing_loc_row else None
            )

            if existing_loc:
                loc_id = existing_loc["id"]
                # Collect existing aliases to merge new ones
                current_aliases_set = (
                    set(existing_loc["aliases"].split(","))
                    if existing_loc["aliases"]
                    else set()
                )
                new_aliases_from_param = (
                    set(aliases_string.split(",")) if aliases_string else set()
                )

                merged_aliases_set = current_aliases_set.union(new_aliases_from_param)
                # Filter out empty strings that might result from splitting empty or ",," strings
                merged_aliases_list = [
                    a.strip() for a in merged_aliases_set if a.strip()
                ]
                final_aliases_string = ",".join(
                    sorted(merged_aliases_list)
                )  # Sort for consistency

                # Update existing location
                cursor.execute(
                    "UPDATE locations SET name = ?, aliases = ? WHERE id = ?",
                    (name, final_aliases_string, loc_id),
                )
                logger.info(
                    f"Updated existing location: {name} (slug: {slug}), Merged aliases: {final_aliases_string}"
                )
            else:
                # Insert new location
                cursor.execute(
                    "INSERT INTO locations (name, slug, aliases) VALUES (?, ?, ?)",
                    (name, slug, aliases_string),
                )
                loc_id = cursor.lastrowid
                logger.info(f"Added new location: {name} (slug: {slug})")
            conn.commit()
            return loc_id

    def log_location_update(self, loc_slug: str, ingame_date: str, description: str):
        """Logs a historical update for a location."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM locations WHERE slug = ?", (loc_slug,))
            row = cursor.fetchone()
            if row:
                loc_id = row["id"]
                cursor.execute(
                    """
                    INSERT INTO location_history (location_id, ingame_date, description)
                    VALUES (?, ?, ?)
                """,
                    (loc_id, ingame_date, description),
                )
                conn.commit()
                logger.info(f"Logged history update for location '{loc_slug}'.")
            else:
                logger.warning(
                    f"Location with slug '{loc_slug}' not found for logging history update. Event: {description}"
                )

    def get_location_list_for_prompt(self):
        """
        Prepares a list of all locations for the LLM prompt.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, slug, aliases FROM locations")
            rows = cursor.fetchall()

            # Format as a text block for the LLM
            loc_list = []
            for row in rows:
                loc_list.append(
                    f"Name: {row['name']} | Slug: {row['slug']} | Aliases: [{row['aliases']}]"
                )
            return "\n".join(loc_list)

    def get_location_by_slug(self, slug: str):
        """
        Retrieves a location by its slug.
        Returns the location as a dictionary or None if not found.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM locations WHERE slug = ? COLLATE NOCASE", (slug,)
            )
            row = cursor.fetchone()
            return self._row_to_dict(row)
