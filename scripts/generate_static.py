import os
import shutil
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

from scripts.db_manager import DatabaseManager


def convert_to_dict(obj):
    """Konvertiert sqlite3.Row zu normalem dict."""
    if isinstance(obj, dict):
        return obj
    try:
        return dict(obj)
    except:
        return obj


def get_safe_list(items):
    """Konvertiert Liste von Rows zu Liste von Dicts."""
    if not items:
        return []
    return [convert_to_dict(item) for item in items]


def generate_static():
    """Generiert statische HTML-Dateien mit direktem Jinja2 Rendering."""
    
    print("=" * 60)
    print("Starte statische Seitengenerierung...")
    print("=" * 60)
    print()
    
    # Output-Verzeichnis erstellen
    public_dir = Path("public")
    if public_dir.exists():
        shutil.rmtree(public_dir)
    public_dir.mkdir(exist_ok=True)
    
    # Datenbank initialisieren
    print("Initialisiere Datenbank...")
    try:
        db = DatabaseManager()
        all_chars = db.get_all_characters()
        print(f"OK ({len(all_chars)} Charaktere gefunden)")
    except Exception as e:
        print(f"FEHLER: {e}")
        traceback.print_exc()
        return
    
    print()
    
    # Jinja2 Environment einrichten
    print("Richte Jinja2 Environment ein...")
    try:
        env = Environment(loader=FileSystemLoader("app/templates"))
        print("OK")
    except Exception as e:
        print(f"FEHLER: {e}")
        traceback.print_exc()
        return
    
    print()
    
    # Alle Daten vorbereiten (einmal laden)
    print("Lade Daten...")
    try:
        pcs = get_safe_list(db.get_all_characters(char_type="PC"))
        npcs = get_safe_list(db.get_all_characters(char_type="NPC"))
        all_characters = get_safe_list(db.get_all_characters())
        latest_session = convert_to_dict(db.get_latest_session())
        total_sessions = db.get_sessions_count()
        
        print(f"OK (PCs: {len(pcs)}, NPCs: {len(npcs)}, Sessions: {total_sessions})")
    except Exception as e:
        print(f"FEHLER: {e}")
        traceback.print_exc()
        return
    
    print()
    
    # Standard-Context
    base_context = {
        "pcs": pcs,
        "npcs": npcs
    }
    
    # ============== STATISCHE SEITEN ==============
    print("Generiere statische Seiten:")
    print("-" * 60)
    
    static_pages = [
        ("index.html", "index.html", {"session": latest_session}),
        ("characters.html", "characters/index.html", {"pcs": pcs, "npcs": npcs}),
        ("chronik.html", "chronik/index.html", {
            "sessions": get_safe_list(db.get_all_sessions(limit=5, offset=0)),
            "total_sessions": total_sessions,
            "current_page": 1,
            "total_pages": max(1, (total_sessions + 4) // 5)
        }),
    ]
    
    errors = []
    
    for template_name, output_path, extra_context in static_pages:
        try:
            print(f"  {output_path:<30}", end=" ")
            
            # Context zusammenstellen
            context = {**base_context, **extra_context}
            
            # Template rendern
            template = env.get_template(template_name)
            html = template.render(**context)
            
            # Speichern
            output_file = public_dir / output_path
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(html, encoding="utf-8")
            
            file_size = len(html)
            print(f"OK ({file_size} bytes)")
            
        except Exception as e:
            print(f"ERROR: {str(e)[:50]}")
            errors.append(f"{output_path}: {str(e)}")
            traceback.print_exc()
    
    # ============== CHARACTER-DETAIL SEITEN ==============
    print()
    print("Generiere Character Detail Seiten:")
    print("-" * 60)
    print(f"  Gesamt: {len(all_characters)} Charaktere\n")
    
    success_count = 0
    
    for idx, char in enumerate(all_characters, 1):
        try:
            char = convert_to_dict(char)
            slug = char.get("slug")
            
            if not slug:
                print(f"  [{idx:2d}] {char.get('name', 'UNKNOWN'):<30} SKIPPED (no slug)")
                continue
            
            char_name = char.get("name", "UNKNOWN")
            output_path = f"characters/{slug}/index.html"
            
            print(f"  [{idx:2d}] {char_name:<30}", end=" ")
            
            # Character-Bilder laden
            images = db.get_character_images(char.get("id", 0))
            
            # Context zusammenstellen
            context = {
                **base_context,
                "char": char,
                "images": images
            }
            
            # Template rendern
            template = env.get_template("character_detail.html")
            html = template.render(**context)
            
            # Speichern
            output_file = public_dir / output_path
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(html, encoding="utf-8")
            
            print("OK")
            success_count += 1
            
        except Exception as e:
            print(f"ERROR: {str(e)[:50]}")
            errors.append(f"Character {idx} ({char.get('name', 'UNKNOWN')}): {str(e)}")
            # traceback.print_exc()
    
    print(f"\n  ✓ {success_count}/{len(all_characters)} erfolgreich")
    
    # ============== STATISCHE ASSETS ==============
    print()
    print("Kopiere statische Assets:")
    print("-" * 60)
    
    static_src = Path("app/static")
    static_dst = public_dir / "static"
    
    if static_src.exists():
        if static_dst.exists():
            shutil.rmtree(static_dst)
        shutil.copytree(static_src, static_dst)
        file_count = sum(1 for _ in static_dst.rglob("*") if _.is_file())
        print(f"  Kopiert: app/static → public/static ({file_count} Dateien)")
    else:
        print(f"  Warnung: app/static nicht gefunden")
    
    # ============== BILDER ==============
    print()
    print("Kopiere Bilder:")
    print("-" * 60)
    
    img_src = Path("docs/img")
    img_dst = public_dir / "img"
    
    if img_src.exists():
        if img_dst.exists():
            shutil.rmtree(img_dst)
        shutil.copytree(img_src, img_dst)
        file_count = sum(1 for _ in img_dst.rglob("*") if _.is_file())
        print(f"  Kopiert: docs/img → public/img ({file_count} Dateien)")
    else:
        print(f"  Warnung: docs/img nicht gefunden")
    
    # ============== ZUSAMMENFASSUNG ==============
    print()
    print("=" * 60)
    if errors:
        print(f"⚠️  Fertig mit {len(errors)} FEHLERN")
        print("-" * 60)
        for err in errors[:10]:
            print(f"  ❌ {err}")
        if len(errors) > 10:
            print(f"  ... und {len(errors) - 10} weitere Fehler")
    else:
        print("✅ Fertig! Statische Seitengenerierung erfolgreich")
    print("=" * 60)
    print()
    print(f"Output-Verzeichnis: {public_dir.resolve()}")
    print()
    
    # Statistik
    html_files = list(public_dir.rglob("*.html"))
    if html_files:
        total_size = sum(f.stat().st_size for f in html_files)
        print(f"Generierte Dateien:")
        print(f"  HTML-Dateien: {len(html_files)}")
        print(f"  Gesamtgroesse: {total_size / 1024:.1f} KB")
    print()


if __name__ == "__main__":
    try:
        generate_static()
        print("SUCCESS: Deployment ready!")
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)

