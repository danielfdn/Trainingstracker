"""Einstiegspunkt der Anwendung.

Starten aus dem Ordner backend/:
    uvicorn app.main:app --reload

Danach liegt die interaktive Doku auf http://127.0.0.1:8000/docs
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.main import api_router
from app.core.config import settings

# main.py -> app -> backend -> Projekt-Root -> frontend/dist
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Damit die PWA (anderer Port/Origin) die API aufrufen darf.
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Einfacher Lebenszeichen-Endpunkt (praktisch fuers Deployment)."""
    return {"status": "ok"}


def _ist_api(path: str) -> bool:
    """Unbekannte API-Pfade duerfen NICHT auf die index.html zurueckfallen.

    Sonst antwortet ein Tippfehler in der URL mit HTML und dem Status 200 -
    der Client bekaeme also "Erfolg" und eine Seite, wo er JSON erwartet.
    """
    return path.startswith("api/") or path == "api"


class SpaStaticFiles(StaticFiles):
    """Statische Dateien mit Rueckfall auf die index.html.

    Ein Pfad wie /u/3/log existiert als Datei nicht - er ist eine Route des
    React-Routers. Ohne diesen Rueckfall gaebe es beim Neuladen oder beim
    Oeffnen eines Links darauf eine 404, und die installierte App waere nach
    jedem Neustart auf der Startseite. html=True allein genuegt nicht: das
    greift nur fuer Verzeichnisse, nicht fuer beliebige Routen.
    """

    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as fehler:
            # StaticFiles WIRFT die 404, es gibt sie nicht als Antwort
            # zurueck - ein Blick auf response.status_code allein wuerde
            # hier also nie greifen.
            if fehler.status_code != 404 or _ist_api(path):
                raise
            return await super().get_response("index.html", scope)
        if response.status_code == 404 and not _ist_api(path):
            return await super().get_response("index.html", scope)
        return response


# --- Die gebaute PWA ausliefern -------------------------------------------
#
# Im Betrieb liefert dieses Backend auch das Frontend aus, unter derselben
# Herkunft. Das ist die Voraussetzung dafuer, dass die App auf dem iPhone
# installierbar ist: Ein Service Worker braucht HTTPS, und eine HTTPS-Seite
# darf keine HTTP-API aufrufen. Eine Herkunft loest beides auf einmal - und
# CORS entfaellt dabei gleich mit.
#
# Nur aktiv, wenn frontend/dist existiert (also nach "npm run build").
# In der Entwicklung laeuft das Frontend weiter auf Port 5173 mit CORS.
if FRONTEND_DIST.is_dir():

    @app.get("/manifest.webmanifest", include_in_schema=False)
    def manifest() -> FileResponse:
        """Eigener Handler wegen des Medientyps - ohne den korrekten Typ
        ignoriert Safari das Manifest und bietet keine Installation an."""
        return FileResponse(
            FRONTEND_DIST / "manifest.webmanifest",
            media_type="application/manifest+json",
        )

    @app.get("/sw.js", include_in_schema=False)
    def service_worker() -> FileResponse:
        """Der Service Worker darf NICHT lange zwischengespeichert werden -
        sonst bleibt eine alte Version haengen und die App aktualisiert sich
        nie mehr."""
        return FileResponse(
            FRONTEND_DIST / "sw.js",
            media_type="text/javascript",
            headers={"Cache-Control": "no-cache"},
        )

    # Ganz zuletzt eingehaengt, damit /api/... und /health weiterhin die
    # Endpunkte oben treffen.
    app.mount("/", SpaStaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
