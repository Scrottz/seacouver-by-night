from pathlib import Path
from typing import Optional  # Import Optional for type hints

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

        # Check if session already exists, if not, insert a placeholder
        session = self.db.get_session_by_date(session_date)
        if not session:
            logger.info(f"Session for date {session_date} not found. Inserting placeholder.")
            self.db.insert_session(session_date, notes_content, session_date, f"Session {session_date}")
            session = self.db.get_session_by_date(session_date) # Re-fetch to get the ID

        session_id = session['id'] # Get the session ID for logging

        # 2. Phase 1: Generate Chronicle
        logger.info(f"Generating narrative for {session_date}...")
        chronicle = self.llm.generate_chronicle(prev_narrative, notes_content, npc_list, last_date, location_list)

        if not chronicle:
            logger.error("Chronicle generation failed. Aborting session update.")
            return

        # Update the session with generated chronicle content
        self.db.update_session_ai_content(
            session_date,
            chronicle.get('title', session.get('title', 'Unknown Title')),
            chronicle.get('ingame_date', session.get('ingame_date', 'Unknown Date')),
            chronicle.get('narrative', session.get('narrative', 'No narrative provided.')),
            chronicle.get('summary', session.get('summary', 'No summary provided.'))
        )
        # Re-fetch session to get potentially updated ingame_date from chronicle
        session = self.db.get_session_by_date(session_date)
        session_ingame_date = session.get('ingame_date', 'Unknown Date')


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
            # --- Process new or updated locations FIRST to ensure they exist in 'locations' table ---
            # This loop handles both new locations and new aliases for existing locations
            for loc_data in metadata.get('new_or_updated_locations', []):
                name = loc_data.get('name')
                slug = loc_data.get('slug')
                aliases = loc_data.get('aliases')

                if not slug:
                    logger.warning(f"Location data missing 'slug'. Skipping: {loc_data}")
                    continue
                if not name: # Fallback: use slug as name if not provided
                    name = slug.replace('-', ' ').title()

                self.db.add_location(
                    name=name,
                    slug=slug,
                    aliases=aliases # This will be correctly processed by the updated add_location
                )

            # --- Now process specific location history events for already existing locations ---
            for loc_history_data in metadata.get('location_history_events', []):
                slug = loc_history_data.get('slug')
                description = loc_history_data.get('description')
                ingame_date_event = loc_history_data.get('ingame_date')

                if not slug or not description:
                    logger.warning(f"Location history event missing 'slug' or 'description'. Skipping: {loc_history_data}")
                    continue

                # Ensure the location exists before logging history (add_location handles creation/update)
                # Note: If LLM only provides history for a NEW location it didn't list in new_or_updated_locations,
                # this would fail. The prompt should guide it to list new locations first.
                existing_loc_check = self.db.get_location_by_slug(slug)
                if not existing_loc_check:
                    logger.warning(f"Location with slug '{slug}' not found for history event. Skipping event: {description}")
                    continue

                self.db.log_location_update(
                    loc_slug=slug,
                    ingame_date=ingame_date_event or session_ingame_date, # Use event-specific date or session's
                    description=description
                )

            # Sync tasks
            for task in metadata.get('tasks', []):
                self.db.sync_task(
                    session_id, # Use the retrieved session_id
                    task.get('description'),
                    task.get('status'),
                    task.get('reason'),
                    task.get('id') # Pass task ID if it's an update to an existing task
                )

            # Process NPC updates
            for npc in metadata.get('npc_updates', []):
                source_char = self.db.get_character_by_slug(npc['slug'])
                if not source_char:
                    logger.warning(f"NPC with slug '{npc['slug']}' not found in DB for updates. Skipping.")
                    continue

                # Update character stats (Status, Bio, Contacts, etc.)
                update_data = {
                    k: v for k, v in npc.items()
                    if k in ['status', 'contact', 'friends_raw', 'foes_raw', 'cause_of_death'] and v is not None
                }
                if npc.get('biography_addition'):
                    # The update_character_from_ai_data handles appending for 'biography' field
                    # Note: We pass 'biography_addition' key, and the db_manager method explicitly checks for it
                    update_data['biography_addition'] = npc['biography_addition']

                if update_data: # Only call if there's something to update
                    self.db.update_character_from_ai_data(npc['slug'], **update_data)

                # Add/Update Aliases for NPC
                if npc.get('alias'):
                    self.db.add_alias_to_character(npc['slug'], npc['alias'])

                # Process relationships (the new logic in db_manager handles type restriction and reason list)
                for rel in npc.get('relations', []):
                    # The prompt specified 'reason' as a single string for this part.
                    # db_manager.update_npc_relationship will take this single reason and add it to the JSON list.
                    self.db.update_npc_relationship(
                        source_slug=npc['slug'],
                        target_slug=rel['target_slug'],
                        new_relation_type=rel['type'], # This is validated in db_manager
                        new_reason=rel['reason'],      # This will be added to the JSON list
                        session_id=session_id
                    )

                # Process interaction logs (specific events between characters)
                for interaction in npc.get('interaction_logs', []):
                    target_char = self.db.get_character_by_slug(interaction['target_slug'])
                    if target_char:
                        self.db.log_character_interaction(
                            source_id=source_char['id'],
                            target_id=target_char['id'],
                            ingame_date=interaction.get('ingame_date', session_ingame_date), # Use interaction's date if provided, else session's
                            change_desc=interaction['change'],
                            reason=interaction['reason'],
                            session_id=session_id
                        )
                    else:
                        logger.warning(f"Target NPC with slug '{interaction['target_slug']}' not found for interaction log. Skipping.")

                # Process general NPC log if provided by LLM
                if npc.get('log'):
                    self.db.log_character_interaction(
                        source_id=source_char['id'],
                        target_id=None, # No specific target for a general NPC log
                        ingame_date=session_ingame_date,
                        change_desc=f"General activity: {npc['log']}", # Use 'log' as description
                        reason=npc['log'], # Use 'log' content as reason for this log entry
                        session_id=session_id
                    )

        logger.info(f"Session {session_date} fully processed.")
