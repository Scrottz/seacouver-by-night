import os
import json
import yaml
from openai import OpenAI
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class AIEngine:
    def __init__(self, prompt_file="prompts.yaml"):
        # Load prompt configuration
        with open(prompt_file, 'r', encoding='utf-8') as f:
            self.prompts = yaml.safe_load(f)
        
        # OpenRouter Client (Claude/Sonnet/etc.)
        self.or_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        
        # Gemini Client
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.gemini_model = genai.GenerativeModel('gemini-2.0-flash')

    def generate_chronicle_sonnet(self, notes, prev_narrative, npc_list):
        """
        Uses Sonnet via OpenRouter for the creative, atmospheric narrative.
        """
        prompt = self.prompts['chronicle_processor']['user_prompt'].format(
            prev_narrative=prev_narrative or "Beginning of chronicle.",
            notes=notes,
            npc_list=", ".join(npc_list)
        )
        
        response = self.or_client.chat.completions.create(
            model="anthropic/claude-3.5-sonnet",
            messages=[
                {"role": "system", "content": self.prompts['chronicle_processor']['system']},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)

    def analyze_status_gemini(self, narrative):
        """
        Uses Gemini for fast, structural tasks like status extraction.
        """
        prompt = f"Analyze this text and extract NPC status updates as JSON: {narrative}"
        
        response = self.gemini_model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)

# ================= TEST BLOCK =================
if __name__ == "__main__":
    engine = AIEngine()
    print("AIEngine initialisiert.")
    
    # Beispiel für einen Test-Call
    # result = engine.generate_chronicle("Notes...", "Prev...", ["Victor", "Liora"])
    # print(result)
