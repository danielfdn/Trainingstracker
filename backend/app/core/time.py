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
