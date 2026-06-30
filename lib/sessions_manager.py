
from pathlib import Path

from lib.db_manager import DatabaseManager
from lib.llm_processor import LLMProcessor
from lib.log_utils import get_logger

logger = get_logger("session_manager")

class SessionManager:
    def __init__(self):
        self.db = DatabaseManager()
        self.llm = LLMProcessor()

    def update_session(self, note_file_path: Path):
        """
        Orchestrates the two-phase process:
        1. Generate narrative and session content.
        2. Extract tasks, NPC metadata, and location updates into the database.
        """
        notes_content = note_file_path.read_text(encoding="utf-8")
        session_date = note_file_path.stem

        # 1. Retrieve context
        prev_session = self.db.get_previous_session(session_date)
        last_date = prev_session.get("ingame_date") if prev_session else "2015-09-25"
        prev_narrative = prev_session.get("narrative") if prev_session else "The story begins..."

        npc_list = self.db.get_npc_list_for_prompt()
        location_list = self.db.get_location_list_for_prompt()
        active_tasks = self.db.get_all_active_tasks()

        # 2. Phase 1: Generate Chronicle
        logger.info(f"Generating narrative for {session_date}")
        chronicle = self.llm.generate_chronicle(prev_narrative, notes_content, npc_list, last_date)

        if not chronicle:
            logger.error("Chronicle generation failed.")
            return

        self.db.update_session_ai_content(
            session_date, chronicle['title'], chronicle['ingame_date'],
            chronicle['narrative'], chronicle['summary']
        )

        # 3. Phase 2: Metadata Extraction (Archivist)
        logger.info("Extracting metadata...")
        metadata = self.llm.extract_metadata(
            chronicle['narrative'],
            notes_content,
            npc_list,
            tasks_list=active_tasks,
            location_list=location_list
        )

        if metadata:
            session = self.db.get_session_by_date(session_date)

            # Sync tasks
            for task in metadata.get('tasks', []):
                self.db.sync_task(
                    session['id'], task.get('description'), task.get('status'),
                    task.get('reason'), task.get('id')
                )

            # Process NPC updates
            for npc in metadata.get('npc_updates', []):
                # Update character stats (Status, Bio, Contacts, etc.)
                update_data = {
                    k: v for k, v in npc.items()
                    if k in ['status', 'contact', 'friends_raw', 'foes_raw', 'cause_of_death']
                }
                if npc.get('biography_addition'):
                    update_data['biography'] = npc['biography_addition']

                self.db.update_character_from_ai_data(npc['slug'], **update_data)

                # Update relationship logs (The new interaction_logs table)
                source_char = self.db.get_character_by_slug(npc['slug'])
                if source_char:
                    for interaction in npc.get('interaction_logs', []):
                        target_char = self.db.get_character_by_slug(interaction['target_slug'])
                        if target_char:
                            self.db.log_character_interaction(
                                source_char['id'], target_char['id'],
                                chronicle['ingame_date'], interaction['change'], interaction['reason']
                            )

                    # Update relationships (for the old relationship table)
                    for rel in npc.get('relations', []):
                        self.db.update_npc_relationship(
                            npc['slug'], rel['target_slug'], rel['type'], rel['reason'], session['id']
                        )

                    # Update aliases
                    if npc.get('alias'):
                        self.db.add_alias_to_character(npc['slug'], npc['alias'])

            # Process location updates
            for loc in metadata.get('location_updates', []):
                self.db.log_location_update(
                    loc['slug'],
                    loc['ingame_date'],
                    loc['description']
                )

        logger.info(f"Session {session_date} fully processed.")
