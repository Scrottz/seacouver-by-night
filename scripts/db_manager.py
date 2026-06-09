
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
                    foes_raw TEXT
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

            # Prepare values for insert/update, using kwargs or existing data
            values = {
                "name": name,
                "slug": slug,
                "type": char_type,
                "player_name": kwargs.get("player_name", existing_char["player_name"] if existing_char else ""),
                "clan": kwargs.get("clan", existing_char["clan"] if existing_char else ""),
                "affiliation": kwargs.get("affiliation", existing_char["affiliation"] if existing_char else ""),
                "contact": kwargs.get("contact", existing_char["contact"] if existing_char else ""),
                "status": kwargs.get("status", existing_char["status"] if existing_char else ""),
                "notes": kwargs.get("notes", existing_char["notes"] if existing_char else ""),
                "biography": kwargs.get("biography", existing_char["biography"] if existing_char else ""),
                "image_path": kwargs.get("image_path", existing_char["image_path"] if existing_char else ""),
                "aliases": kwargs.get("aliases", existing_char["aliases"] if existing_char else ""),
                "friends_raw": kwargs.get("friends_raw", existing_char["friends_raw"] if existing_char else ""),
                "foes_raw": kwargs.get("foes_raw", existing_char["foes_raw"] if existing_char else ""),
            }
            
            if existing_char:
                # Update existing character
                update_query = '''
                    UPDATE characters SET 
                    slug=?, type=?, player_name=?, clan=?, affiliation=?, contact=?, 
                    status=?, notes=?, biography=?, image_path=?, aliases=?, friends_raw=?, foes_raw=? 
                    WHERE name=?
                '''
                params = (
                    values["slug"], values["type"], values["player_name"], values["clan"], 
                    values["affiliation"], values["contact"], values["status"], values["notes"], 
                    values["biography"], values["image_path"], values["aliases"], 
                    values["friends_raw"], values["foes_raw"],
                    name 
                )
                cursor.execute(update_query, params)
                char_id = existing_char["id"]
            else:
                # Insert new character
                # 13 columns: name, slug, type, player_name, clan, affiliation, contact, status, notes, biography, image_path, aliases, friends_raw, foes_raw
                # WAIT: I counted 14 columns in the CREATE TABLE. Let's be precise.
                insert_query = '''
                    INSERT INTO characters
                    (name, slug, type, player_name, clan, affiliation, contact, status, notes, biography, image_path, aliases, friends_raw, foes_raw)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''
                params = (
                    values["name"], values["slug"], values["type"], values["player_name"], 
                    values["clan"], values["affiliation"], values["contact"], values["status"], 
                    values["notes"], values["biography"], values["image_path"], values["aliases"], 
                    values["friends_raw"], values["foes_raw"]
                )
                # Let's double check the count:
                # 1:name, 2:slug, 3:type, 4:player_name, 5:clan, 6:affiliation, 7:contact, 8:status, 9:notes, 10:biography, 11:image_path, 12:aliases, 13:friends_raw, 14:foes_raw
                # That is 14 columns.
                
                # CORRECTED INSERT:
                insert_query = '''
                    INSERT INTO characters
                    (name, slug, type, player_name, clan, affiliation, contact, status, notes, biography, image_path, aliases, friends_raw, foes_raw)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''
                params = (
                    values["name"], values["slug"], values["type"], values["player_name"], 
                    values["clan"], values["affiliation"], values["contact"], values["status"], 
                    values["notes"], values["biography"], values["image_path"], values["aliases"], 
                    values["friends_raw"], values["foes_raw"]
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
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if char_type:
                cursor.execute("SELECT * FROM characters WHERE type = ?", (char_type,))
            else:
                cursor.execute("SELECT * FROM characters")
            return [dict(row) for row in cursor.fetchall()]

    def get_character_by_slug(self, slug):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM characters WHERE slug = ?", (slug,))
            row = cursor.fetchone()
            return dict(row) if row else None


    def get_latest_session(self):
        """
        Holt den neuesten Session-Eintrag.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM sessions ORDER BY date DESC LIMIT 1"
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_sessions(self, limit=2, offset=0):
        """
        Holt alle Sessions mit Pagination.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM sessions ORDER BY date DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_sessions_count(self):
        """
        Gibt die Gesamtzahl der Sessions zurück.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM sessions")
            row = cursor.fetchone()
            return row["count"] if row else 0

    def get_character_by_id(self, char_id):
        """
        Holt Character nach ID.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM characters WHERE id = ?", (char_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_character_images(self, character_id):
        """
        Holt alle Bilder für einen Character.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT image_path FROM character_images WHERE character_id = ? ORDER BY id",
                (character_id,)
            )
            return [row["image_path"] for row in cursor.fetchall()]

# ================= TEST BLOCK =================
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
        biography="Liora has discovered the secret of the Prince's basement."
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
        foes_raw="The Anarchs"
    )
    db.add_character_image(npc_id, "img/npc/victor_caruso_1.png")
    
    print(f"✓ Success: Added Liora (ID: {pc_id}) and Victor (ID: {npc_id}).")
    
    print("\n--- Retrieving all characters ---")
    all_chars = db.get_all_characters()
    for c in all_chars:
        print(f"- ID: {c['id']}, Name: {c['name']}, Type: {c['type']}, Aliases: {c['aliases']}, Friends: {c['friends_raw']}, Foes: {c['foes_raw']}")
        
    print("\n--- Retrieving character by slug ---")
    char_by_slug = db.get_character_by_slug("victor_caruso")
    if char_by_slug:
        print(f"Found by slug: {char_by_slug['name']} (Clan: {char_by_slug['clan']})")
    else:
        print("Character not found by slug.")

    print("\n✓ DatabaseManager tests completed successfully!")
