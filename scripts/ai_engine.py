import os
import re
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class AIEngine:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        self.model_name = "anthropic/claude-sonnet-4.5"

    def process_session(self, plain_notes, previous_narrative, npc_list):
        npc_context = ", ".join([f"{npc['name']} ({npc['clan']})" for npc in npc_list])
        prompt = self._build_prompt(plain_notes, previous_narrative, npc_context)

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system", 
                        "content": (
                            "You are the 'Master Chronicler of Seacouver'. Your writing style is Gothic Horror: "
                            "melancholic, elegant, dark, and atmospheric. "
                            "IMPORTANT: ALL YOUR OUTPUT MUST BE IN GERMAN. "
                            "You write in the third person. You are a precise archivist; you do not invent events."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            return self._parse_response(content)

        except Exception as e:
            print(f"  ! API Error: {e}")
            return None

    def _build_prompt(self, notes, prev_narrative, npcs):
        return f"""
        LANGUAGE REQUIREMENT:
        All output (Narrative, Summary, and Tasks) MUST be written in GERMAN.
        
        ROLE:
        You are the 'Master Chronicler of Seacouver'. Your writing style is Gothic Horror: 
        melancholic, elegant, dark, and atmospheric. You write in the third person.
        
        CONTEXT: 
        This is a fictional narrative for a 'Vampire: The Masquerade' tabletop RPG. 
        All content is stylized fiction.
        
        KNOWN NPCs (Use these names exactly):
        {npcs}
        
        CONTINUITY (The story ended here):
        {prev_narrative if prev_narrative else "This is the beginning of the chronicle."}
        
        CURRENT SESSION RAW NOTES:
        {notes}
        
        STRICT CONSTRAINTS:
        1. NO HALLUCINATIONS: Do not invent events, dialogues, or plot twists that are not present in the raw notes.
        2. NO OUTLOOKS: Do not add an epilogue, a summary of future events, or artificial cliffhangers at the end.
        3. HARD STOP: End the narrative exactly where the raw notes end.
        4. NO META-TALK: Do not add any introductory or concluding remarks.
        
        YOUR TASKS:
        1. NARRATIVE (in German): Transform the raw notes into a seamless, atmospheric story. 
           Use the format [NPC Name](npc:NPC_Name_with_underscores) for linking.
           
        2. SUMMARY (in German): Create a short, punchy teaser (2-3 sentences) for the landing page. 
           
        3. TASKS (in German): Extract all open goals or mysteries as a bulleted list.
        
        OUTPUT FORMAT:
        You MUST use these exact markers to separate the sections:
        ---NARRATIVE---
        [The full story]
        ---SUMMARY---
        [The short summary]
        ---TASKS---
        - Task 1
        - Task 2
        """

    def _parse_response(self, content):
        """
        Robust parser using Regular Expressions to extract content between markers.
        """
        try:
            # Regex to find everything between ---MARKER--- and the next marker or end of string
            # re.DOTALL allows the dot (.) to match newlines
            narrative_match = re.search(r"---NARRATIVE---(.*?)---SUMMARY---", content, re.DOTALL)
            summary_match = re.search(r"---SUMMARY---(.*?)---TASKS---", content, re.DOTALL)
            tasks_match = re.search(r"---TASKS---(.*)", content, re.DOTALL)
            
            narrative = narrative_match.group(1).strip() if narrative_match else ""
            summary = summary_match.group(1).strip() if summary_match else ""
            tasks_text = tasks_match.group(1).strip() if tasks_match else ""
            
            # Clean up tasks list
            tasks = [t.strip("- ").strip() for t in tasks_text.split("\n") if t.strip()]
            
            # If everything is empty, the AI probably failed the format entirely
            if not narrative and not summary and not tasks:
                raise ValueError("No content found between markers")
                
            return {
                "narrative": narrative,
                "summary": summary,
                "tasks": tasks
            }
        except Exception as e:
            print(f"  ! Parsing Error: {e}")
            print(f"  Raw content received:\n{content}")
            return None

# ================= TEST BLOCK =================
if __name__ == "__main__":
    try:
        engine = AIEngine()
        
        sample_npcs = [
            {"name": "Victor Caruso", "clan": "Tremere"},
            {"name": "Sami ibn Khaldun", "clan": "Banu Haqim"},
            {"name": "Liora", "clan": "Malkavian"}
        ]
        
        sample_prev_narrative = (
            "Die Gruppe verließ das brennende Gebäude, während die Schreie der "
            "Söldner hinter ihnen verhallten. Sie wussten, dass der Prinz sie nun "
            "beobachtete, doch die Angst war einer kalten Entschlossenheit gewichen."
        )
        
        sample_notes = """
        - Treffen mit Prinz Victor im Thronsaal
        - Victor ist wütend über den Diebstahl des Bildes
        - Samir ibn Khaldun droht mit Gewalt
        - Liora bemerkt eine seltsame Aura im Raum
        - Auftrag: Findet den Verräter bis zum nächsten Vollmond
        - Ziel: Infiltrieren des Clubs Vertigo
        """
        
        print(f"Sending test request to OpenRouter ({engine.model_name})...")
        result = engine.process_session(sample_notes, sample_prev_narrative, sample_npcs)
        
        if result:
            print("\n" + "="*60)
            print("AI GENERATED NARRATIVE:")
            print("="*60)
            print(result['narrative'])
            print("\n" + "="*60)
            print("AI GENERATED SUMMARY:")
            print("="*60)
            print(result['summary'])
            print("\n" + "="*60)
            print("AI GENERATED TASKS:")
            print("="*60)
            for task in result['tasks']:
                print(f"- {task}")
            print("="*60)
        else:
            print("No result returned from AI.")
            
    except Exception as e:
        print(f"Fatal error during test: {e}")
