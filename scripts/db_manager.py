import sqlite3
import os
import re

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
            cursor = conn.cursor()

            # Characters table with all fields
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS characters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    slug TEXT UNIQUE,
                    type TEXT,
                    player_name TEXT,
                    clan TEXT,
                    affiliation TEXT,
                    contact TEXT,
                    status TEXT,
                    notes TEXT,
                    biography TEXT,
                    image_path TEXT,
                    aliases TEXT,
                    friends_raw TEXT,
                    foes_raw TEXT,
                    location TEXT DEFAULT NULL,
                    cause_of_death TEXT DEFAULT NULL
                )
            ''')

            # Character Images table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS character_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    character_id INTEGER,
                    image_path TEXT,
                    FOREIGN KEY(character_id) REFERENCES characters(id)
                )
            ''')

            # Sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE,
                    ingame_date TEXT,
                    title TEXT,
                    plain_notes TEXT,
                    narrative TEXT,
                    summary TEXT
                )
            ''')

            # Tasks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    description TEXT,
                    status TEXT DEFAULT 'Open',
                    session_id INTEGER,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
            ''')
            conn.commit()

    def _generate_slug(self, name):
        return re.sub(r'[^a-z0-9]', '_', name.lower().strip())

    def add_character(self, name, char_type="NPC", **kwargs):
        slug = self._generate_slug(name)
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Fetch existing character data if available
            cursor.execute("SELECT * FROM characters WHERE name = ?", (name,))
            existing_char = cursor.fetchone()
            existing_dict = self._row_to_dict(existing_char)

            # Prepare values for insert/update, using kwargs or existing data
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
                # Update existing character
                update_query = '''
                    UPDATE characters SET
                    slug=?, type=?, player_name=?, clan=?, affiliation=?, contact=?,
                    status=?, notes=?, biography=?, image_path=?, aliases=?, friends_raw=?, foes_raw=?,
                    location=?, cause_of_death=?
                    WHERE name=?
                '''
                params = (
                    values["slug"], values["type"], values["player_name"], values["clan"],
                    values["affiliation"], values["contact"], values["status"], values["notes"],
                    values["biography"], values["image_path"], values["aliases"],
                    values["friends_raw"], values["foes_raw"],
                    values["location"], values["cause_of_death"],
                    name
                )
                cursor.execute(update_query, params)
                char_id = existing_dict["id"]
            else:
                # Insert new character
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

    def add_character_image(self, character_id, image_path):
        with self.get_connection() as conn:
            conn.execute("INSERT INTO character_images (character_id, image_path) VALUES (?, ?)", (character_id, image_path))
            conn.commit()

    def get_all_characters(self, char_type=None):
        """Gibt alle Charaktere als echte Dictionaries zurück."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if char_type:
                cursor.execute("SELECT * FROM characters WHERE type = ? ORDER BY name", (char_type,))
            else:
                cursor.execute("SELECT * FROM characters ORDER BY name")
            
            # ✓ Alle Rows zu echten dicts konvertieren
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_character_by_slug(self, slug):
        """Gibt einen Charakter als echtes Dictionary zurück."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM characters WHERE slug = ?", (slug,))
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
            # ✓ Alle Rows zu echten dicts konvertieren
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
            # ✓ Als echte Liste von strings zurückgeben
            return [row["image_path"] for row in cursor.fetchall()]


# TEST BLOCK
if __name__ == "__main__":
    print("Testing DatabaseManager...")
    # Clean start for testing
    if os.path.exists("data/test_campaign.db"):
        os.remove("data/test_campaign.db")

    db = DatabaseManager(db_path="data/test_campaign.db")

    # Test adding a PC with all new fields
    pc_id = db.add_character(
        name="Liora Mikhailov",
        char_type="PC",
        clan="Malkavian",
        player_name="Josi",
        aliases="Whisper",
        friends_raw="Alistar Ionman, Marius Raimondi",
        foes_raw="Victor Caruso",
        biography="Liora has discovered the secret of the Prince's basement.",
        location="Seacouver"
    )
    db.add_character_image(pc_id, "img/pc/liora_mikhailov_1.png")
    db.add_character_image(pc_id, "img/pc/liora_mikhailov_2.png")

    # Test adding an NPC
    npc_id = db.add_character(
        name="Victor Caruso",
        char_type="NPC",
        clan="Tremere",
        affiliation="Camarilla",
        status="Alive",
        notes="The Prince of Seacouver.",
        aliases="The Prince",
        friends_raw="Silas Mercer",
        foes_raw="The Anarchs",
        location="Seacouver"
    )
    db.add_character_image(npc_id, "img/npc/victor_caruso_1.png")

    print(f"Success: Added Liora (ID: {pc_id}) and Victor (ID: {npc_id}).")

    print("\n--- Retrieving all characters ---")
    all_chars = db.get_all_characters()
    for c in all_chars:
        print(f"- ID: {c['id']}, Name: {c['name']}, Type: {c['type']}, Location: {c['location']}")

    print("\n--- Retrieving character by slug ---")
    char_by_slug = db.get_character_by_slug("victor_caruso")
    if char_by_slug:
        print(f"Found by slug: {char_by_slug['name']} (Clan: {char_by_slug['clan']}, Location: {char_by_slug['location']})")
    else:
        print("Character not found by slug.")

    print("\nDatabaseManager tests completed successfully!")
