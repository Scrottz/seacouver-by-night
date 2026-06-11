from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
import os
import sys

# Import Database Manager
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
from scripts.db_manager import DatabaseManager

# Initialisiere FastAPI
app = FastAPI()

# Datenbank
db = DatabaseManager()

# Templates
templates = Jinja2Templates(directory="app/templates")

# Statische Dateien
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/img", StaticFiles(directory="docs/img"), name="img")


# ============== HELPER FUNCTIONS ==============
def get_safe_dict(value):
    """Konvertiert sqlite3.Row oder andere Objekte zu dict."""
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    try:
        return dict(value)
    except (TypeError, ValueError):
        return value


def get_all_pcs_safe():
    """Holt alle Spieler-Charaktere als echte Dicts."""
    chars = db.get_all_characters(char_type="PC")
    return [get_safe_dict(c) for c in chars]


def get_all_npcs_safe():
    """Holt alle NPCs als echte Dicts."""
    chars = db.get_all_characters(char_type="NPC")
    return [get_safe_dict(c) for c in chars]


# ============== ROUTES ==============

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Home-Seite mit letztem Session."""
    latest_session = db.get_latest_session()
    
    context = {
        "request": request,
        "session": get_safe_dict(latest_session),
        "pcs": get_all_pcs_safe(),
        "npcs": get_all_npcs_safe()
    }
    
    return templates.TemplateResponse("index.html", context)


@app.get("/characters", response_class=HTMLResponse)
async def characters(request: Request):
    """Alle Charaktere - Übersichtsseite."""
    pcs = get_all_pcs_safe()
    npcs = get_all_npcs_safe()
    
    context = {
        "request": request,
        "pcs": pcs,
        "npcs": npcs
    }
    
    return templates.TemplateResponse("characters.html", context)


@app.get("/characters/{slug}", response_class=HTMLResponse)
async def character_detail(slug: str, request: Request):
    """
    Charakter-Detailseite.
    
    URL: /characters/liora_mikhailov
    """
    # Character aus DB laden
    char = db.get_character_by_slug(slug)
    
    # Wenn nicht gefunden → 404
    if not char:
        return {"error": "Character not found"}, 404
    
    # Sicher zu dict konvertieren
    char = get_safe_dict(char)
    
    # Bilder für Galerie
    images = db.get_character_images(char.get("id", 0))
    
    context = {
        "request": request,
        "char": char,
        "images": images,
        "pcs": get_all_pcs_safe(),
        "npcs": get_all_npcs_safe()
    }
    
    return templates.TemplateResponse("character_detail.html", context)


@app.get("/chronik", response_class=HTMLResponse)
async def chronik(request: Request, page: int = 1):
    """
    Session-Chronik mit Pagination.
    
    URL: /chronik?page=1
    """
    # Pagination
    items_per_page = 5
    offset = (page - 1) * items_per_page
    
    # Sessions laden
    sessions = db.get_all_sessions(limit=items_per_page, offset=offset)
    total_count = db.get_sessions_count()
    total_pages = max(1, (total_count + items_per_page - 1) // items_per_page)
    
    # Sicherstellen, dass page valid ist
    page = max(1, min(page, total_pages))
    
    # Alle zu echten dicts konvertieren
    sessions = [get_safe_dict(s) for s in sessions]
    
    context = {
        "request": request,
        "sessions": sessions,
        "total_sessions": total_count,
        "current_page": page,
        "total_pages": total_pages,
        "pcs": get_all_pcs_safe(),
        "npcs": get_all_npcs_safe()
    }
    
    return templates.TemplateResponse("chronik.html", context)


# ============== STARTUP EVENT ==============
@app.on_event("startup")
async def startup_event():
    """Wird beim Starten ausgeführt."""
    print("🦇 Vampire: The Masquerade PBP Server")
    print("=" * 50)
    print(f"📍 http://localhost:8000")
    print()
    
    # Datenbank-Stats
    all_chars = db.get_all_characters()
    pcs = [c for c in all_chars if c.get("type") == "PC"]
    npcs = [c for c in all_chars if c.get("type") == "NPC"]
    sessions_count = db.get_sessions_count()
    
    print(f"📊 Datenbank-Status:")
    print(f"   ✓ Characters geladen: {len(all_chars)}")
    print(f"   ✓ PCs: {len(pcs)}")
    print(f"   ✓ NPCs: {len(npcs)}")
    print(f"   ✓ Sessions: {sessions_count}")
    print()
    print("=" * 50)
