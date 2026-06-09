import os
import re

# ================= CONFIGURATION =================
INPUT_FILE = "notes/legacy.md"
OUTPUT_DIR = "notes"
# Only these years will be split into individual files
VALID_YEARS = ["2025", "2026"]
# =================================================

def split_legacy_notes():
    """
    Splits a legacy markdown file into individual session files,
    but ONLY for the years specified in VALID_YEARS.
    """
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Input file {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex to find dates in format DD.MM.YYYY inside headers (#, ##, ###)
    date_pattern = r"(#+).*?(\d{2})\.(\d{2})\.(\d{4})"
    
    # Find all matches of dates in the file
    matches = list(re.finditer(date_pattern, content))
    
    if not matches:
        print("No dates found in the legacy file.")
        return

    print(f"Found {len(matches)} total date markers. Filtering for {VALID_YEARS}...")

    files_created = 0
    for i in range(len(matches)):
        match = matches[i]
        day = match.group(2)
        month = match.group(3)
        year = match.group(4)
        
        # ONLY process if the year is in our valid list (2025, 2026)
        if year in VALID_YEARS:
            # Create filename in YYYY-MM-DD format
            filename = f"{year}-{month}-{day}.md"
            filepath = os.path.join(OUTPUT_DIR, filename)

            # Extract the content for this session
            start_pos = match.start()
            # The content ends where the NEXT date match begins, regardless of its year
            end_pos = matches[i+1].start() if i + 1 < len(matches) else len(content)
            
            session_content = content[start_pos:end_pos].strip()

            with open(filepath, 'w', encoding='utf-8') as out_file:
                out_file.write(session_content)
            
            files_created += 1
            print(f"  ✓ Created: {filename}")
        else:
            # Log that we are skipping this date (e.g. 2015)
            print(f"  - Skipping date {day}.{month}.{year} (not in VALID_YEARS)")

    print(f"\nSuccessfully split {files_created} sessions into {OUTPUT_DIR}/")

if __name__ == "__main__":
    split_legacy_notes()
