import os #test2
import glob
from openai import OpenAI

# ================= CONFIGURATION =================
# OpenRouter uses the OpenAI-compatible client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

# Model identifier for OpenRouter - STAYING WITH GEMMA
AI_MODEL = "google/gemma-4-31b-it:free"

# Paths (Relative to project root)
NOTES_DIR = "notes"
DOCS_DIR = "docs"
CHRONIK_DIR = os.path.join(DOCS_DIR, "chronik")
PERSONEN_DIR = os.path.join(DOCS_DIR, "personen")

# IMPORTANT: Images are now inside the docs folder so MkDocs can see them
NPC_IMG_DIR = os.path.join(DOCS_DIR, "img/npc")

# Target files
NPC_FILE = os.path.join(PERSONEN_DIR, "npcs.md")
INDEX_FILE = os.path.join(DOCS_DIR, "index.md")
# =================================================

def ensure_dirs():
    """Ensure all required directories exist."""
    os.makedirs(CHRONIK_DIR, exist_ok=True)
    os.makedirs(PERSONEN_DIR, exist_ok=True)
    os.makedirs(NPC_IMG_DIR, exist_ok=True)

def generate_npc_gallery():
    """
    Scans the images folder and creates a Markdown table.
    """
    print("Generating NPC gallery...")
    content = "# Dramatis Personae\n\nDie bekannten Gesichter der Stadt.\n\n"
    content += "| Porträt | Name |\n| :---: | :--- |\n"

    if not os.listdir(NPC_IMG_DIR):
        print("  ! Warning: No images found in docs/img/npc")
        return

    images = [f for f in os.listdir(NPC_IMG_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]

    for img in sorted(images):
        name = os.path.splitext(img)[0].replace('_', ' ')
        img_path = f"../img/npc/{img}"
        content += f"| ![]({img_path}) | {name} |\n"

    with open(NPC_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ NPC gallery updated: {NPC_FILE}")

def process_notes_with_ai():
    """
    Reads bullet points from /notes, uses AI to write a narrative text,
    and saves it to /docs/chronik.
    """
    print("Processing session notes with AI via OpenRouter...")
    all_notes = sorted(glob.glob(os.path.join(NOTES_DIR, "*.md")))
    latest_session_text = ""

    # FIX for MkDocs Warning: Create a landing page for the chronik folder
    chronik_index_path = os.path.join(CHRONIK_DIR, "index.md")
    with open(chronik_index_path, "w", encoding="utf-8") as f:
        f.write("# Die Chronik\n\nHier sind alle bisherigen Sitzungen der Kampagne aufgelistet.")

    for note_path in all_notes:
        if "legacy" in note_path:
            continue

        filename = os.path.basename(note_path)
        target_path = os.path.join(CHRONIK_DIR, filename)

        if not os.path.exists(target_path):
            print(f"  -> Generating text for {filename}...")
            with open(note_path, "r", encoding="utf-8") as f:
                bullet_points = f.read()

            try:
                response = client.chat.completions.create(
                    model=AI_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a master chronicler of a 'Vampire: The Masquerade' campaign. "
                                "Your task is to transform short, bullet-point notes into an atmospheric, "
                                "dark, and elegant narrative text. Use language that reflects "
                                "melancholy, power, and the Gothic-Horror feeling. "
                                "Write in the third person, in German."
                            )
                        },
                        {"role": "user", "content": f"Here are the session notes:\n\n{bullet_points}"}
                    ],
                    temperature=0.7
                )
                text = response.choices[0].message.content
                title = f"Sitzung {os.path.splitext(filename)[0]}"
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(f"# {title}\n\n{text}")
            except Exception as e:
                print(f"  ! Error processing {filename}: {e}")
        else:
            print(f"  - {filename} already exists, skipping.")

    processed_sessions = sorted(glob.glob(os.path.join(CHRONIK_DIR, "*.md")))
    # Filter out index.md for the teaser
    session_files = [f for f in processed_sessions if "index.md" not in f]
    
    if session_files:
        with open(session_files[-1], "r", encoding="utf-8") as f:
            full_text = f.read()
            lines = full_text.split('\n')
            body = "\n".join(lines[1:])
            latest_session_text = body[:600] + "..."

    return latest_session_text

def update_index(summary):
    """Updates the home page with the latest teaser."""
    print("Updating home page...")
    content = (
        "# 🩸 Die Chroniken von Seacouver\n\n"
        "Willkommen im Archiv der Nächte von Seacouver. Hier werden die Taten, Verrate und "
        "Blutpakte unserer Coterie festgehalten.\n\n"
        "## 🌑 Letzte Ereignisse\n\n"
        f"{summary}\n\n"
        "[Weiterlesen in der Chronik](/chronik/)\n\n"
        "---\n"
        "*Die Nacht ist jung, doch die Zeit der Vampire ist endlos.*"
    )
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ Home page updated: {INDEX_FILE}")

if __name__ == "__main__":
    try:
        ensure_dirs()
        generate_npc_gallery()
        summary = process_notes_with_ai()
        update_index(summary)
        print("\nBuild preparation successfully completed!")
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        exit(1)
