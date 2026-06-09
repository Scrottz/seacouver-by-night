
import sys
import os
import math

# Damit Python die scripts/db_manager.py findet
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from scripts.db_manager import DatabaseManager

app = FastAPI()

# Mount static files for images and CSS
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/img", StaticFiles(directory="docs/img"), name="img")

templates = Jinja2Templates(directory="app/templates")
db = DatabaseManager(db_path="data/campaign.db")

# Konfiguration
SESSIONS_PER_PAGE = 2


# ===== CONTEXT PROCESSOR =====
# Diese Funktion wird vor jedem Template aufgerufen
def _get_sidebar_data():
    """
    Lädt die Sidebar-Daten (PCs und NPCs).
    """
    pcs = db.get_all_characters(char_type="PC")
    npcs = db.get_all_characters(char_type="NPC")
    return {
        "pcs": pcs,
        "npcs": npcs
    }


# Überschreibe die TemplateResponse um Context Processor zu nutzen
original_template_response = templates.TemplateResponse

def custom_template_response(request, name, context=None, **kwargs):
    """
    Wrapper um TemplateResponse, der automatisch Sidebar-Daten hinzufügt.
    """
    if context is None:
        context = {}
    
    # Sidebar-Daten immer hinzufügen
    sidebar_data = _get_sidebar_data()
    context.update(sidebar_data)
    context["request"] = request
    
    return original_template_response(
        request=request,
        name=name,
        context=context,
        **kwargs
    )


# Ersetze die original TemplateResponse Methode
templates.TemplateResponse = custom_template_response


@app.get("/")
async def index(request: Request):
    """
    Homepage: Zeigt den letzten Session-Eintrag.
    """
    latest_session = db.get_latest_session()
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"session": latest_session}
    )


@app.get("/chronik")
async def chronik(request: Request, page: int = 1):
    """
    Chronik: Alle Sessions mit Pagination.
    """
    total_sessions = db.get_sessions_count()
    total_pages = math.ceil(total_sessions / SESSIONS_PER_PAGE)
    
    # Sicherstellen, dass page gültig ist
    if page < 1:
        page = 1
    if page > total_pages and total_pages > 0:
        page = total_pages
    
    offset = (page - 1) * SESSIONS_PER_PAGE
    sessions = db.get_all_sessions(limit=SESSIONS_PER_PAGE, offset=offset)
    
    return templates.TemplateResponse(
        request=request, 
        name="chronik.html", 
        context={
            "sessions": sessions,
            "current_page": page,
            "total_pages": total_pages,
            "total_sessions": total_sessions
        }
    )


@app.get("/characters")
async def characters(request: Request):
    """
    Zeigt alle Spieler-Charaktere und NPCs.
    """
    pcs = db.get_all_characters(char_type="PC")
    npcs = db.get_all_characters(char_type="NPC")
    
    return templates.TemplateResponse(
        request=request, 
        name="characters.html", 
        context={"pcs": pcs, "npcs": npcs}
    )


@app.get("/character/{slug}")
async def character_profile(request: Request, slug: str):
    """
    Character-Detail-Seite.
    """
    char = db.get_character_by_slug(slug)
    if not char:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            status_code=404
        )
    
    # Zusatzbilder laden
    images = db.get_character_images(char["id"])
    
    return templates.TemplateResponse(
        request=request, 
        name="character_detail.html", 
        context={"char": char, "images": images}
    )
