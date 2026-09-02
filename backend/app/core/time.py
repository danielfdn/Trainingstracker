"""Hilfen fuer den Umgang mit Zeitstempeln.

Hintergrund: Die Spalten sind als DateTime(timezone=True) deklariert.
PostgreSQL (timestamptz) gibt daraus aware datetimes zurueck, SQLite - das
in den Tests genutzt wird - kennt keine Zeitzonen und liefert naive Werte.
Ueber die API kommen dagegen immer aware Werte herein ("...Z").

Ein Vergleich oder eine Subtraktion aus beiden Welten wirft
"can't compare offset-naive and offset-aware datetimes". Deshalb werden
Zeitstempel vor jedem Rechnen durch as_utc() geschickt.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.core.config import settings


def as_utc(value: datetime | None) -> datetime | None:
    """Macht aus einem naiven Zeitstempel einen UTC-behafteten.

    Naive Werte stammen immer aus der Datenbank und sind dort in UTC
    abgelegt - die Annahme ist also korrekt, nicht geraten.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def local_month(value: datetime) -> tuple[int, int]:
    """(Jahr, Monat) des Zeitpunkts in der konfigurierten Zeitzone.

    Erst nach UTC normalisieren, dann in die lokale Zone rechnen: eine
    Einheit am 31.08. um 23:30 Ortszeit gehoert zum August, auch wenn sie
    in UTC schon der 01.09. ist.
    """
    lokal = as_utc(value).astimezone(ZoneInfo(settings.TIMEZONE))
    return lokal.year, lokal.month


def month_key(value: datetime) -> str:
    """Monat als "2026-04" - sortierbar und als Schluessel brauchbar."""
    jahr, monat = local_month(value)
    return f"{jahr:04d}-{monat:02d}"


def parse_month(value: str) -> tuple[int, int]:
    """Wandelt "2026-04" in (2026, 4). Wirft ValueError bei Unsinn."""
    try:
        jahr_text, monat_text = value.split("-")
        jahr, monat = int(jahr_text), int(monat_text)
    except (ValueError, AttributeError):
        raise ValueError(f"'{value}' ist kein Monat im Format JJJJ-MM") from None
    if not 1 <= monat <= 12:
        raise ValueError(f"'{value}' hat keinen gueltigen Monat (1-12)")
    return jahr, monat
