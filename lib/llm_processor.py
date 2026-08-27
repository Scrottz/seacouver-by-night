import json
import os
import re
from pathlib import Path
from typing import Any, Optional

import openai
import yaml
from dotenv import load_dotenv

from lib.log_utils import get_logger

logger = get_logger("llm_processor")

PROMPT_PATH = Path("res/prompts/chronik_prompt.yaml")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODEL_NAME = "anthropic/claude-sonnet-4.6"


class LLMProcessor:
    def __init__(
        self, prompt_path: Path = PROMPT_PATH, model_name: str = MODEL_NAME
    ) -> None:
        load_dotenv()
        api_key = os.getenv("OPENROUTER_API_KEY")

        self.client = openai.OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://seacouver-by-night.local",
                "X-Title": "Seacouver By Night",
            },
        )
        self.model_name = model_name
        self.prompts = self._load_prompts(prompt_path)

    def _load_prompts(self, path: Path) -> dict[str, str]:
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return {
                    "chronicle": f"{data['chronicle_generator']['system_prompt']}\n\n{data['chronicle_generator']['user_prompt']}",
                    "archivist": f"{data['data_archivist']['system_prompt']}\n\n{data['data_archivist']['user_prompt']}",
                }
        except Exception as e:
            logger.error(f"Failed to load prompt file at {path}: {e}")
            raise

    def generate_chronicle(
        self,
        prev_narrative: str,
        notes: str,
        npc_list: list[dict],
        last_date: str,
        location_list: list[dict],
    ) -> Optional[dict[str, Any]]:
        formatted_prompt = self.prompts["chronicle"].format(
            prev_narrative=prev_narrative,
            notes=notes,
            npc_list=json.dumps(npc_list),
            last_date=last_date,
            location_list=location_list,
        )
        return self._call_api(formatted_prompt)

    # HIER: location_list hinzugefügt
    def extract_metadata(
        self,
        narrative: str,
        notes: str,
        npc_list: list[dict],
        tasks_list: list[dict],
        location_list: str,
    ) -> Optional[dict[str, Any]]:
        """Extrahiert Tasks, NPC-Updates und Location-Updates."""
        formatted_prompt = self.prompts["archivist"].format(
            narrative=narrative,
            notes=notes,
            npc_list=json.dumps(npc_list),
            tasks_list=json.dumps(tasks_list),
            location_list=location_list,  # Wird nun an das Prompt-Template übergeben
        )
        return self._call_api(formatted_prompt)

    def _call_api(self, prompt: str) -> Optional[dict[str, Any]]:
        try:
            logger.info(f"Sending request to {self.model_name} via OpenRouter")
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            text = content.replace("```json", "").replace("```", "").strip()

            # Robustes Parsing
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                logger.warning("Standard JSON load failed, attempting repair...")
                # Ersetze unescaped Newlines innerhalb von Strings durch \n
                repaired = re.sub(r"(?<!\\)\n", "\\n", text)
                return json.loads(repaired)
        except Exception as e:
            logger.error(f"Error calling OpenRouter: {e}")
            return None
