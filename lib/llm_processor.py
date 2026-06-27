import json
import os

import google.generativeai as genai
from dotenv import load_dotenv

from lib.logging import get_logger

load_dotenv()
logger = get_logger("llm_processor")

MODEL_NAME = "gemini-3.5-flash"

class LLMProcessor:
    def __init__(self, system_prompt: str):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY nicht in .env gefunden!")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=system_prompt,
            generation_config={"response_mime_type": "application/json"}
        )

    def generate_chronicle(self, user_prompt: str) -> dict:
        try:
            response = self.model.generate_content(user_prompt)
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"KI-Fehler: {e}")
            return None
