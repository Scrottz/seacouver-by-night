
import os
from openai import OpenAI
from dotenv import load_dotenv
from db_manager import DatabaseManager

# Load environment variables
load_dotenv()

class BioGenerator:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        self.model_name = "anthropic/claude-sonnet-4.5"

    def generate_bio(self, npc_name, basic_info, chronicle_snippets):
        """
        Generates a factual biography based ONLY on chronicle evidence.
        """
        prompt = f"""
        ROLE:
        You are a precise historian of Seacouver. Your task is to write a brief, 
        factual biography of an NPC based ONLY on the provided chronicle snippets.
        
        NPC BASIC INFO:
        {basic_info}
        
        CHRONICLE EVIDENCE:
        {chronicle_snippets}
        
        STRICT CONSTRAINTS:
        1. NO HALLUCINATIONS: Do not invent any facts, traits, or events. 
        2. SOURCE ONLY: Use ONLY the provided 'CHRONICLE EVIDENCE'. If the evidence 
           does not contain enough information to write a biography, return exactly: "No further information available."
        3. STYLE: Write in a neutral, archival style in German.
        4. LENGTH: Keep it concise (max 3-5 sentences).
        5. LANGUAGE: The output must be in GERMAN.
        
        OUTPUT:
        Write only the biography. No introductory text.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a precise historian. You do not hallucinate. You write in German."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2 # Very low temperature for maximum factuality
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"  ! API Error during bio generation for {npc_name}: {e}")
            return None

def run_bio_update():
    """
    Main loop to update all NPC biographies based on their mentions in the chronicle.
    """
    db = DatabaseManager()
    bio_gen = BioGenerator()
    
    npcs = db.get_all_npcs()
    print(f"Starting biography update for {len(npcs)} NPCs using {bio_gen.model_name}...")

    for npc in npcs:
        name = npc['name']
        print(f"Processing {name}...")

        # 1. Find all session narratives where this NPC is mentioned
        with db.get_connection() as conn:
            cursor = conn.cursor()
            # We search for the name in the narrative column of the sessions table
            cursor.execute("SELECT narrative FROM sessions WHERE narrative LIKE ?", (f"%{name}%",))
            relevant_snippets = [row[0] for row in cursor.fetchall()]

        if not relevant_snippets:
            print(f"  - No mentions of {name} found in the chronicle. Skipping.")
            continue

        # 2. Build the context
        # Combine all snippets into one block of text
        chronicle_context = "\n\n".join([f"Session Snippet:\n{s}" for s in relevant_snippets])
        
        # Basic info from DB (Clan, Affiliation, etc.)
        basic_info = f"Name: {name}, Clan: {npc.get('clan', 'Unknown')}, Affiliation: {npc.get('affiliation', 'Unknown')}"

        # 3. Generate the biography
        bio = bio_gen.generate_bio(name, basic_info, chronicle_context)
        
        if bio:
            # Update the NPC in the database
            db.update_npc_biography(name, bio)
            print(f"  ✓ Biography updated for {name}")
        else:
            print(f"  ! Failed to generate bio for {name}")

if __name__ == "__main__":
    try:
        run_bio_update()
        print("\nAll NPC biographies have been processed.")
    except Exception as e:
        print(f"Fatal error during bio update: {e}")
