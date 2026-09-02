# Umbau auf SQLAlchemy + FastAPI-Standardstruktur

Dieses Dokument beschreibt in einfachen Worten, was ich am Backend geändert
habe und welche Fehler mir dabei im alten Code aufgefallen sind.

**Status:** 14 Tests laufen grün (`uv run pytest`), die App startet und alle
25 Endpunkte sind registriert.

---

## 1. Was sich an der Ordnerstruktur geändert hat

Vorher lagen `entities/`, `repositories/` und `api/` teils unter `backend/`,
teils unter `backend/app/`, dazu ein leeres `backend/db.py`. Jetzt liegt alles
unter `backend/app/` – das ist die Struktur, die auch das
`full-stack-fastapi-template` verwendet:

```
backend/
├── alembic/              # Migrationen (neu)
├── alembic.ini           # (neu)
├── app/
│   ├── main.py           # FastAPI-App, CORS, bindet den API-Router ein (neu)
│   ├── core/
│   │   ├── config.py     # Einstellungen aus .env (neu)
│   │   └── db.py         # Engine + Session-Factory (neu)
│   ├── entities/         # ORM-Modelle (umgebaut)
│   ├── schemas/          # Pydantic-Schemas für die API (neu)
│   ├── repositories/     # Datenzugriff (umgebaut)
│   └── api/
│       ├── deps.py       # Dependency Injection (neu)
│       ├── main.py       # sammelt alle Router ein (ersetzt Tutorial-Code)
│       └── routes/       # ein Modul pro Ressource (neu)
└── tests/                # (neu)
```

Warum eine Ebene tiefer (`backend/app/`)? Damit `app` ein sauberes
Python-Package ist. Vorher standen in den Dateien Importe wie
`from entities.set import Set` – die funktionieren nur, wenn du zufällig aus
genau dem richtigen Ordner startest. Jetzt heißt es überall
`from app.entities.set import Set`, und das funktioniert immer, wenn du aus
`backend/` startest.

**Starten:**

```bash
cd backend
uv run uvicorn app.main:app --reload
# Doku: http://127.0.0.1:8000/docs
```

---

## 2. Entities: aus einfachen Klassen wurden ORM-Modelle

Vorher war `Exercise` eine normale Python-Klasse mit `__init__`. Jetzt erbt
sie von `Base` und beschreibt damit gleichzeitig die Datenbanktabelle:

```python
class Exercise(Base):
    __tablename__ = "exercise"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    sets: Mapped[list["Set"]] = relationship(back_populates="exercise", ...)
```

Wichtig für unsere frühere Diskussion: **Ich habe die Aufteilung „eine Datei
pro Modell" beibehalten.** Möglich wird das durch zwei Details:

- `relationship()` bekommt den Klassennamen als **String** (`"Set"`), nicht als
  importiertes Objekt. Dadurch entstehen keine zirkulären Importe. Die echten
  Importe stehen nur in einem `if TYPE_CHECKING:`-Block – die sieht der
  Type-Checker, zur Laufzeit werden sie nie ausgeführt.
- `app/entities/__init__.py` importiert alle Modelle. Das ist der Sammelpunkt,
  den Alembic braucht: Ein Modell landet nur in `Base.metadata`, wenn sein
  Modul auch wirklich importiert wurde.

### Die Beziehungen zwischen den Tabellen

```
User ──1:n──> WorkoutPlan ──1:n──> Exercise ──1:n──> Set
                    └──────1:n──> Workout
```

Alle mit `ON DELETE CASCADE`: Löschst du einen User, verschwinden seine Pläne,
Übungen, Sätze und Workouts mit. Das ist getestet
(`test_delete_user_raeumt_abhaengige_daten_auf`).

### Eine Design-Entscheidung, die du kennen solltest

Deine ursprüngliche `User`-Klasse hatte **einen** `workout_plan`. Ich habe
daraus **`workout_plans` (eine Liste)** gemacht.

Grund: Mit nur einem Plan pro User könntest du keine Historie führen – sobald
du im Herbst einen neuen Plan anlegst, wäre der Sommerplan weg, und alle
`Workout`-Einträge, die daran hängen, mit ihm. Für einen Trainingstracker ist
genau diese Historie aber der Kern.

Falls du im Frontend „den aktuellen Plan" brauchst: den holst du dir über
`starting_date`/`ending_date` (die Sortierung dafür ist in
`WorkoutPlanRepo.list_by_user` schon eingebaut). Wenn du das anders willst,
sag Bescheid – das ist eine Fachentscheidung, keine technische.

### Tabellennamen

- `User` → Tabelle **`appuser`** (`user` ist in PostgreSQL reserviert – das
  hattest du schon richtig gemacht).
- `Set` → Tabelle **`exercise_set`**. `set` ist ebenfalls reserviert (die
  `SET`-Klausel im `UPDATE`). Das wäre dir spätestens beim ersten
  `CREATE TABLE set` um die Ohren geflogen.

### Datentypen

- Gewichte sind `Numeric` statt `Float`. `Float` rechnet binär und produziert
  Rundungsfehler (80.1 + 0.2 ≠ 80.3); `Numeric` speichert exakte
  Dezimalstellen.
- `Workout.date` ist `DateTime(timezone=True)`. Ohne Zeitzone wäre ein
  Training, das du im Urlaub loggst, später um Stunden verschoben.
- `Set.weight` darf `NULL` sein – Klimmzüge haben nun mal kein Gewicht.

---

## 3. Repositories: SQLAlchemy statt psycopg2

Das ist der Teil, über den wir vorher gesprochen hatten: **Die Repo-Schicht
bleibt, ihr Inhalt wird ersetzt.**

### Vorher

```python
class BaseRepo:
    def __init__(self):
        self.connection = psycopg2.connect(...)   # jede Instanz eine Verbindung
        self.cursor = self.connection.cursor()

    def fetchone(self, query, params=None): ...
```

### Nachher

```python
class BaseRepo(Generic[ModelType]):
    def __init__(self, session: Session, model: type[ModelType]):
        self.session = session      # wird von außen hereingegeben
        self.model = model
```

Drei Dinge sind dadurch besser geworden:

1. **Verbindungen werden nicht mehr geleakt.** Vorher öffnete jede
   Repo-Instanz eine eigene Verbindung, die nie geschlossen wurde – bei jedem
   Request eine mehr, bis PostgreSQL keine mehr annimmt. Jetzt gibt es genau
   eine `Engine` mit Connection-Pool, und `get_session()` in `api/deps.py`
   gibt die Session per `try/finally` garantiert zurück.

2. **Kein CRUD-Code mehr doppelt.** `get`, `list`, `count`, `create`,
   `update`, `delete` stehen einmal im `BaseRepo`. Deine konkreten Repos
   enthalten nur noch das, was wirklich speziell ist:

   | Repo              | Eigene Methoden                      |
   | ----------------- | ------------------------------------ |
   | `UserRepo`        | `get_by_name`, `get_with_plans`      |
   | `WorkoutPlanRepo` | `list_by_user`, `get_with_exercises` |
   | `ExerciseRepo`    | `list_by_plan`, `get_with_sets`      |
   | `SetRepo`         | `list_by_exercise`                   |
   | `WorkoutRepo`     | `list_by_plan`, `list_by_user`       |

   `WorkoutRepo`, `SetRepo` und `WorkoutPlanRepo` standen vorher auf `pass` –
   die sind jetzt vollständig.

3. **Testbar ohne echte Datenbank.** Weil die Session hereingereicht wird,
   können die Tests einfach eine SQLite-DB im Arbeitsspeicher unterschieben.
   Genau deshalb laufen die 14 Tests in 0,13 Sekunden ohne laufenden Postgres.

Zum `Generic[ModelType]`: Das sorgt dafür, dass `UserRepo(session).get(1)` für
den Type-Checker ein `User | None` ist und nicht irgendein Objekt – du bekommst
Autovervollständigung auf `.name`, `.age` usw.

### N+1-Abfragen vermieden

Methoden wie `get_with_exercises` nutzen `selectinload`. Ohne das würde
SQLAlchemy für einen Plan mit 8 Übungen 9 einzelne Abfragen schicken (1 für
den Plan + 8 für die Sätze). Mit `selectinload` ist es eine Abfrage pro Ebene.

---

## 4. Neu: Pydantic-Schemas (`app/schemas/`)

Pro Ressource gibt es drei Schemas:

- `*Create` – was beim Anlegen reinkommt (ohne `id`)
- `*Update` – alle Felder optional, für `PATCH`
- `*Public` – was rausgeht (mit `id`)

Damit gehen keine ORM-Objekte direkt über die API nach außen, und die
Validierung passiert automatisch: `age: int = Field(gt=0, lt=130)` lehnt ein
negatives Alter mit einer klaren 422-Antwort ab, bevor irgendetwas in der DB
landet. Dafür brauchst du keine Handarbeit im Service.

Zusätzlich gibt es `WorkoutPlanWithExercises` und `ExerciseWithSets` – die
liefern verschachtelte Daten, damit deine PWA eine Plan-Detailansicht mit einem
einzigen Request laden kann statt mit fünf.

---

## 5. Neu: API-Endpunkte

Der Tutorial-Code (`Item`, In-Memory-Liste) ist raus. Stattdessen gibt es pro
Ressource ein eigenes Router-Modul mit den Standard-CRUD-Routen:

```
POST   /api/v1/users                GET /api/v1/users        GET /api/v1/users/{id}
PATCH  /api/v1/users/{id}           DELETE /api/v1/users/{id}
```

Analog für `/workout-plans`, `/exercises`, `/sets`, `/workouts` – 25 Endpunkte
insgesamt. Dazu `/health` für später beim Deployment.

Ein paar Details, die den Unterschied machen:

- **`exclude_unset=True` bei PATCH.** Ohne das würden Felder, die der Client
  gar nicht geschickt hat, auf `None` gesetzt – du änderst das Gewicht und der
  Name wäre weg.
- **Fremdschlüssel werden vorher geprüft.** Legst du einen Plan für einen
  nicht existierenden User an, bekommst du eine verständliche 404 statt einer
  500 aus der Datenbank.
- **Eine echte Fachregel:** Ein Satz mit Gewicht an einer Übung mit
  `weighted=False` wird mit 422 abgelehnt.
- **CORS ist konfiguriert** (`app/main.py`), damit die PWA später zugreifen
  darf.

---

## 6. Neu: Alembic

Eingerichtet in `backend/alembic/`, mit zwei Anpassungen gegenüber der
Standardvorlage:

- Die Verbindungs-URL kommt aus deiner `.env` (über `app/core/config.py`),
  **nicht** aus `alembic.ini`. So liegen keine Passwörter im Repository.
- `target_metadata = Base.metadata`, damit `--autogenerate` funktioniert.

**Noch offen:** Es gibt noch keine Migrationsdatei. Die zu erzeugen braucht
eine laufende Datenbank, die ich hier nicht habe. Sobald deine DB steht:

```bash
cd backend
uv run alembic revision --autogenerate -m "initial schema"
uv run alembic upgrade head
```

Schau die generierte Datei in `alembic/versions/` vorher durch – Alembic rät
manchmal falsch, gerade bei Typänderungen.

---

## 7. Konfiguration und Abhängigkeiten

- **`app/core/config.py`** liest die `.env` per `pydantic-settings`. Vorteil
  gegenüber `os.getenv()`: Die App scheitert beim Start mit einer klaren
  Meldung, wenn etwas fehlt oder falsch ist – nicht erst beim ersten
  DB-Zugriff. Der `.env`-Pfad wird absolut aus dem Modulpfad berechnet, damit
  es egal ist, aus welchem Ordner du startest.
- **`.env.example`** neu angelegt – dokumentiert, welche Variablen nötig sind,
  ohne echte Zugangsdaten preiszugeben. Deine echte `.env` ist korrekt von
  `.gitignore` ausgeschlossen und nicht im Repo (habe ich geprüft).
- **`pyproject.toml`**: `sqlalchemy`, `alembic`, `pydantic-settings` ergänzt,
  dazu `pytest` und `httpx2` als Dev-Abhängigkeiten.

---

## 8. Gefundene Fehler im alten Code

Das ist die Liste dessen, was beim Umbau aufgefallen ist. Die meisten davon
hätten erst zur Laufzeit zugeschlagen.

### Sicherheitsrelevant

**1. SQL-Injection in `exercise_repo.update_exercise`**

```python
self.execute(f"UPDATE appuser SET name = '{new_name}' WHERE id = %s", (id,))
```

Der f-String setzt die Benutzereingabe direkt in die Query ein. Eine Eingabe
wie `'; DROP TABLE appuser; --` wird dann als SQL ausgeführt. In `user_repo.py`
hattest du es mit `%s` richtig gemacht (samt Kommentar dazu) – hier ist es
durchgerutscht. **Erledigt:** SQLAlchemy parametrisiert grundsätzlich alles.

### Hätten beim ersten Aufruf gekracht

**2. Falsche Tabelle in `update_exercise`** – alle drei `case`-Zweige
schrieben in `appuser` statt `exercise`. Case 2 und 3 setzten außerdem
`SET name = ...`, obwohl sie `weighted` bzw. das Gewicht ändern sollten.

**3. `id` war in `update_exercise` gar nicht definiert.** Die Methode nimmt
`exercise` entgegen, benutzt aber `(id,)` – das ist Pythons eingebaute
`id`-Funktion. Das Ergebnis wäre kein Fehler gewesen, sondern ein stillschweigend
falscher Parameter.

**4. Parameter-Anzahl stimmte in `user_repo.update_user` nicht.**

```python
self.execute("UPDATE appuser SET name = %s WHERE id = %s", (id,))
```

Zwei Platzhalter, ein Parameter → `IndexError`. Betrifft alle drei `case`-Zweige.
Dazu wurden `new_name`/`new_age`/`new_weight` eingelesen, aber nie verwendet.

**5. Fehlendes `@` in `api/main.py`:**

```python
app.get("/items")          # <- kein Decorator, nur ein Aufruf

def list_items(limit: int = 10):
```

Die Route wurde nie registriert, `list_items` war toter Code. Ein leicht zu
übersehender Tippfehler, weil es syntaktisch völlig korrekt ist.

**6. Fehlendes `f` beim f-String:**

```python
raise HTTPException(status_code=404, detail="Item {item_id} not found")
```

Die Fehlermeldung enthielt wörtlich `{item_id}`. Beide Varianten stehen jetzt
als Test abgesichert (`test_unbekannte_id_gibt_404_mit_lesbarer_meldung`).

### Strukturell

**7. Verbindungs-Leak** – siehe Abschnitt 3. Das wäre der Fehler gewesen, der
dich im Betrieb am meisten Zeit gekostet hätte, weil er erst unter Last
auftritt.

**8. `sets` wurden beim Anlegen einer Exercise nie gespeichert.**
`create_exercise` schrieb nur `title` und `weighted` – die Sätze aus dem
übergebenen Objekt gingen still verloren.

**9. Kaputte Importe.** `from entities.workout_plan import WorkoutPlan` in
`app/entities/user.py` – der Ordner heißt aber `app/entities`. Kein Modul war
in dieser Form importierbar.

**10. `input()` in der Repo-Schicht.** `update_user` und `update_exercise`
hatten eine Endlosschleife mit `input()` darin. In einem Webserver würde das
den Request blockieren, bis der Prozess stirbt – es gibt ja keine Konsole, an
der jemand antwortet. (Das hattest du selbst schon als TODO markiert.)

**11. Fehlende `id`-Felder.** `Set`, `Workout` und `WorkoutPlan` hatten keine
`id` – ohne Primärschlüssel lässt sich ein Datensatz weder gezielt lesen noch
ändern noch löschen.

**12. `Exercise` verlangte `sets` als Pflichtparameter.** Du konntest keine
Übung anlegen, ohne vorher schon eine Satz-Liste zu haben – obwohl die Sätze
erst beim Training entstehen.

**13. `BaseRepo.execute(query, params)`** hatte kein `params=None` als Default,
`fetchall`/`fetchone` schon. `BaseRepo.create` war ein leerer Stub mit `pass`.

### Kleinigkeiten

**14. `backend/db.py` war leer** und wurde nie importiert – gelöscht, ersetzt
durch `app/core/db.py`.

**15. `id: int = None`** als Typannotation ist streng genommen falsch, korrekt
wäre `int | None`. Erledigt sich mit den ORM-Modellen.

---

## 9. Was als Nächstes dransteht

1. **Migration erzeugen**, sobald die DB läuft (Abschnitt 6).
2. **Service-Schicht** (`backend/services/` ist noch leer). Aktuell steht die
   Fachlogik in den Routern – das ist bei reinem CRUD völlig in Ordnung. Sobald
   eine Operation mehrere Repos anfasst (z.B. „Plan mit allen Übungen und
   Sätzen in einem Rutsch anlegen") oder etwas berechnet wird (1RM,
   Volumen-Statistiken), gehört das in einen Service.
3. **Authentifizierung** – aktuell gibt es keine. Jeder kann alle User lesen
   und löschen. Bevor das Backend irgendwo öffentlich erreichbar ist, brauchst
   du Login und Tokens.
4. **`venv/` aufräumen** – du hast zwei virtuelle Umgebungen im Projekt
   (`.venv/` von uv und ein älteres `venv/`). Beide sind gitignored, aber das
   alte `venv/` stiftet Verwirrung, weil `VIRTUAL_ENV` bei uv-Befehlen darauf
   zeigt und Warnungen erzeugt.

Zu jedem dieser Punkte erkläre ich dir gerne die Hintergründe – sag einfach,
wo du weitermachen willst.
