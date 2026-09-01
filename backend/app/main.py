"""Einstiegspunkt der Anwendung.

Starten aus dem Ordner backend/:
    uvicorn app.main:app --reload

Danach liegt die interaktive Doku auf http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings

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
