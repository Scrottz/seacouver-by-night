import os
import glob
from collections import Counter

# ================= CONFIGURATION =================
# Path to the folder containing the .md files from Notion export
NOTION_EXPORT_DIR = "data/notion_export"
# =================================================

def analyze_npc_fields():
    """
    Scans all NPC markdown files to identify all unique keys used in the metadata.
    """
    print(f"Analyzing NPC files in {NOTION_EXPORT_DIR}...")
    
    # Find all markdown files
    md_files = glob.glob(os.path.join(NOTION_EXPORT_DIR, "*.md"))
    
    if not md_files:
        print(f"Error: No .md files found in {NOTION_EXPORT_DIR}")
        return

    # Use a Counter to track how many NPCs have which field
    field_counts = Counter()
    total_npcs = len(md_files)

    for file_path in md_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    # We look for lines that contain a colon, which indicates a Key: Value pair
                    if ':' in line:
                        # Split only on the first colon
                        key = line.split(':', 1)[0].strip()
                        # We ignore lines that are likely just part of the text (too long for a key)
                        if len(key) < 50: 
                            field_counts[key] += 1
        except Exception as e:
            print(f"  ! Error reading {os.path.basename(file_path)}: {e}")

    # Sort fields by frequency (most common first)
    sorted_fields = sorted(field_counts.items(), key=lambda x: x[1], reverse=True)

    print("\n" + "="*50)
    print(f"FIELD ANALYSIS REPORT")
    print("="*50)
    print(f"Total NPCs analyzed: {total_npcs}")
    print(f"Unique fields found: {len(sorted_fields)}")
    print("-" * 50)
    print(f"{'Field Name':<30} | {'Frequency':<10} | {'Coverage'}")
    print("-" * 50)

    for field, count in sorted_fields:
        coverage = (count / total_npcs) * 100
        print(f"{field:<30} | {count:<10} | {coverage:>6.1f}%")
    
    print("="*50)
    print("\nRecommendation:")
    print("Fields with high coverage (>80%) should be dedicated columns in the DB.")
    print("Fields with low coverage can be merged into a general 'notes' or 'metadata' field.")

if __name__ == "__main__":
    analyze_npc_fields()
