#!/usr/bin/env bash
#
# Bringt eine laufende Installation auf den neuesten Stand.
#
# Aufruf (von ueberall):
#     ~/Trainingstracker/deploy/update.sh
#
# Macht der Reihe nach das, was nach einer Aenderung noetig ist - und zwar
# vollstaendig. Genau hier gehen sonst Schritte verloren: das Frontend wird
# nur beim Start des Backends eingelesen, und eine Migration, die keiner
# ausfuehrt, faellt erst beim naechsten Klick auf.

# -e  bricht beim ersten Fehler ab, statt froehlich weiterzumachen
# -u  meckert bei unbekannten Variablen, statt "" einzusetzen
# -o pipefail  laesst auch einen Fehler MITTEN in einer Pipe zaehlen
set -euo pipefail

# Das Projektverzeichnis aus dem Ort dieses Skripts ableiten, nicht aus dem
# aktuellen Arbeitsverzeichnis - sonst haengt das Ergebnis davon ab, von wo
# aus man aufruft.
PROJEKT_ORDNER="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJEKT_ORDNER"

DIENST="trainingstracker"

schritt() {
    printf '\n\033[1;36m==> %s\033[0m\n' "$1"
}

hinweis() {
    printf '\033[0;33m    %s\033[0m\n' "$1"
}

# --- Vorbedingungen -------------------------------------------------------
# Lieber hier abbrechen als nach dem git pull mittendrin.
if [[ ! -f .env ]]; then
    echo "FEHLER: .env fehlt in $PROJEKT_ORDNER" >&2
    echo "        cp .env.example .env  und die Zugangsdaten eintragen." >&2
    exit 1
fi

for werkzeug in git uv npm; do
    if ! command -v "$werkzeug" >/dev/null 2>&1; then
        echo "FEHLER: '$werkzeug' nicht gefunden." >&2
        exit 1
    fi
done

# --- 1. Stand holen -------------------------------------------------------
schritt "Aenderungen holen"
VORHER="$(git rev-parse HEAD)"
git pull --ff-only
NACHHER="$(git rev-parse HEAD)"

if [[ "$VORHER" == "$NACHHER" ]]; then
    hinweis "Schon aktuell - die restlichen Schritte laufen trotzdem,"
    hinweis "damit ein halb durchgelaufener Versuch sauber nachgeholt wird."
else
    git --no-pager log --oneline "$VORHER..$NACHHER"
fi

# --- 2. Abhaengigkeiten ---------------------------------------------------
# Beide Installationen sind idempotent: aendert sich nichts, kosten sie nur
# ein paar Sekunden. "npm ci" waere reproduzierbarer, wuerde aber jedes Mal
# node_modules komplett neu bauen - auf einem Pi sind das Minuten.
schritt "Backend-Abhaengigkeiten (uv sync)"
uv sync

schritt "Frontend-Abhaengigkeiten (npm install)"
npm install --silent
npm --prefix frontend install --silent

# --- 3. Datenbank ---------------------------------------------------------
# Vor dem Build, nicht danach: laeuft die Migration schief, soll die alte,
# funktionierende Oberflaeche stehen bleiben.
schritt "Datenbank migrieren (alembic upgrade head)"
(cd backend && uv run alembic upgrade head)

# --- 4. Frontend bauen ----------------------------------------------------
# Der entscheidende Schritt, den man von Hand vergisst: das Backend liest
# frontend/dist beim Start EINMAL ein. Ohne Build aendert sich nichts.
schritt "Frontend bauen (npm run build)"
npm run build

# --- 5. Dienst neu starten ------------------------------------------------
schritt "Dienst neu starten"
if ! command -v systemctl >/dev/null 2>&1; then
    # Auf dem Mac gibt es kein systemd - dort laeuft die App ohnehin per
    # "npm run dev" im Vordergrund.
    hinweis "systemctl nicht vorhanden - nichts neu zu starten."
elif ! systemctl list-unit-files "$DIENST.service" --no-legend | grep -q .; then
    hinweis "Dienst '$DIENST' ist nicht installiert."
    hinweis "Einmalig:  sudo cp deploy/$DIENST.service /etc/systemd/system/"
    hinweis "           sudo systemctl daemon-reload"
    hinweis "           sudo systemctl enable --now $DIENST"
else
    sudo systemctl restart "$DIENST"
    # Kurz warten, sonst meldet systemctl "active", bevor uvicorn ueberhaupt
    # versucht hat, sich mit der Datenbank zu verbinden.
    sleep 2
    if systemctl is-active --quiet "$DIENST"; then
        echo "    $DIENST laeuft."
    else
        echo "FEHLER: $DIENST laeuft nach dem Neustart nicht." >&2
        echo "        journalctl -u $DIENST -n 50 --no-pager" >&2
        exit 1
    fi
fi

schritt "Fertig."
