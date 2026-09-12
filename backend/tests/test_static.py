"""Tests der Auslieferung der gebauten PWA.

Nur relevant, wenn frontend/dist existiert - in der Entwicklung laeuft das
Frontend auf Port 5173, und dann haengt der Mount in main.py gar nicht drin.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import FRONTEND_DIST, _kein_rueckfall

pytestmark = pytest.mark.skipif(
    not FRONTEND_DIST.is_dir(), reason="frontend/dist fehlt - erst 'npm run build'"
)


def test_route_des_routers_bekommt_die_app(client: TestClient) -> None:
    """/u/3/log ist keine Datei, sondern eine Route - die index.html gehoert hin."""
    response = client.get("/u/3/log")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_fehlende_datei_ist_eine_404_und_keine_html_seite(client: TestClient) -> None:
    """Der Fall, der eine installierte PWA still auf einem alten Stand haelt.

    Kommt statt eines fehlenden Bundles die index.html mit Status 200 zurueck,
    behaelt der Browser seinen alten Service Worker - und das Handy laeuft
    weiter auf einem Build von vor Wochen, ohne jede Fehlermeldung.
    """
    for pfad in ("/gibtesnicht.js", "/assets/index-gibtesnicht.js", "/assets/x.css"):
        response = client.get(pfad)
        assert response.status_code == 404, f"{pfad} faellt auf die index.html zurueck"


def test_service_worker_kommt_als_javascript_und_ohne_cache(client: TestClient) -> None:
    """Der eigene Handler in main.py. Mit falschem Medientyp registriert
    Safari ihn nicht, und mit Cache aktualisiert sich die App nie mehr."""
    response = client.get("/sw.js")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/javascript")
    assert response.headers["cache-control"] == "no-cache"


def test_unbekannter_api_pfad_bleibt_eine_404(client: TestClient) -> None:
    assert client.get("/api/v1/gibtesnicht").status_code == 404


@pytest.mark.parametrize(
    "pfad, erwartet",
    [
        ("api/v1/users", True),
        ("api", True),
        ("sw.js", True),
        ("assets/index-abc123.js", True),
        ("manifest.webmanifest", True),
        ("u/3/log", False),
        ("u/3/log/progress", False),
        # Ein Plantitel mit Punkt darf nicht als Datei gelten.
        ("u/3/plans/2.0", False),
    ],
)
def test_rueckfall_entscheidung(pfad: str, erwartet: bool) -> None:
    assert _kein_rueckfall(pfad) is erwartet
