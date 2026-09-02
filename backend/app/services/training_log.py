"""Auswertung der Trainingshistorie.

Warum eine eigene Schicht: Die Router davor machen reines CRUD - ein
Datensatz rein, ein Datensatz raus. Hier wird dagegen gerechnet und ueber
mehrere Repos hinweg gearbeitet. Genau an dieser Stelle lohnt sich die
Service-Schicht, vorher nicht.

Warum in Python statt in SQL: Die Monatszuordnung braucht date_trunc und
AT TIME ZONE, beides gibt es nur in PostgreSQL - die Tests laufen aber auf
einer SQLite-DB im Arbeitsspeicher. Bei der Datenmenge eines einzelnen
Users (ein paar hundert Saetze) kostet das Rechnen im Python nichts und
haelt die Tests dialektfrei.
"""

from collections import defaultdict
from decimal import Decimal

from app.core.time import month_key
from app.entities.set import Set
from app.repositories.set_repo import SetRepo
from app.repositories.workout_repo import WorkoutRepo
from app.schemas.training_log import (
    CUSTOM_LABEL,
    ExerciseMonthStats,
    ExerciseProgress,
    ExerciseProgressDelta,
    MonthOption,
    ProgressComparison,
    WorkoutLogEntry,
)

CENT = Decimal("0.01")


def _label(month: str) -> str:
    """"2026-04" -> "04/2026" - die Schreibweise aus der Spezifikation."""
    jahr, monat = month.split("-")
    return f"{monat}/{jahr}"


def _dauer_text(sekunden: int | None) -> str | None:
    if sekunden is None:
        return None
    stunden, rest = divmod(sekunden, 3600)
    minuten, sekunden = divmod(rest, 60)
    return f"{stunden:02d}:{minuten:02d}:{sekunden:02d}"


def _stats(saetze: list[Set], *, weighted: bool) -> ExerciseMonthStats:
    """Verdichtet die Saetze einer Uebung in einem Monat zu Kennzahlen."""
    gewichte = [s.weight for s in saetze if s.weight is not None]
    wiederholungen = [s.repetitions for s in saetze]

    # Bei Koerpergewichtsuebungen bleibt die Gewichtsspalte leer - dort ist
    # die Wiederholungszahl die einzige Fortschrittszahl.
    bestes_gewicht = max(gewichte) if (weighted and gewichte) else None
    schnitt_gewicht = (
        (sum(gewichte, Decimal(0)) / len(gewichte)).quantize(CENT)
        if (weighted and gewichte)
        else None
    )
    return ExerciseMonthStats(
        best_weight=bestes_gewicht,
        best_reps=max(wiederholungen) if wiederholungen else None,
        avg_reps=round(sum(wiederholungen) / len(wiederholungen), 1) if wiederholungen else None,
        avg_weight=schnitt_gewicht,
        set_count=len(saetze),
        session_count=len({s.workout_id for s in saetze}),
    )


def _differenz(a, b):
    """B minus A, aber nur wenn beide Seiten einen Wert haben."""
    if a is None or b is None:
        return None
    return b - a


class TrainingLogService:
    def __init__(self, workout_repo: WorkoutRepo, set_repo: SetRepo):
        self.workout_repo = workout_repo
        self.set_repo = set_repo

    # --- Ansicht 1: alle vergangenen Einheiten ---------------------------

    def history(self, user_id: int, *, skip: int = 0, limit: int = 100) -> list[WorkoutLogEntry]:
        eintraege = []
        for workout in self.workout_repo.list_for_log(user_id, skip=skip, limit=limit):
            sekunden = workout.duration_seconds
            eintraege.append(
                WorkoutLogEntry(
                    id=workout.id,
                    date=workout.date,
                    attended=workout.attended,
                    comment=workout.comment,
                    # Freie Trainings tragen keinen Trainingstag - in der
                    # Historie erscheinen sie als "Custom".
                    workout_type=(
                        workout.training_day.workout_type
                        if workout.training_day is not None
                        else CUSTOM_LABEL
                    ),
                    is_custom=workout.is_custom,
                    plan_title=workout.workout_plan.title,
                    duration_seconds=sekunden,
                    duration=_dauer_text(sekunden),
                    set_count=len(workout.sets),
                    exercise_count=len({s.exercise_id for s in workout.sets}),
                )
            )
        return eintraege

    # --- Monate, in denen es etwas zu sehen gibt -------------------------

    def months(self, user_id: int) -> list[MonthOption]:
        """Fuellt die beiden Dropdowns - nur Monate mit Einheiten."""
        gezaehlt: defaultdict[str, int] = defaultdict(int)
        for zeitpunkt in self.workout_repo.dates_by_user(user_id):
            gezaehlt[month_key(zeitpunkt)] += 1
        return [
            MonthOption(month=monat, label=_label(monat), workout_count=anzahl)
            for monat, anzahl in sorted(gezaehlt.items(), reverse=True)
        ]

    # --- Ansicht 2: Monat gegen Monat ------------------------------------

    def compare(self, user_id: int, month_a: str, month_b: str) -> ProgressComparison:
        """Vergleicht zwei Kalendermonate je Uebung.

        Eine Uebung erscheint, sobald sie in EINEM der beiden Monate
        vorkam - sonst bliebe unsichtbar, was neu dazugekommen oder
        weggefallen ist. Die fehlende Seite bleibt dann null.
        """
        saetze_je_uebung: defaultdict[int, dict[str, list[Set]]] = defaultdict(
            lambda: {month_a: [], month_b: []}
        )
        uebungen = {}

        for satz in self.set_repo.list_for_analysis(user_id):
            monat = month_key(satz.workout.date)
            if monat not in (month_a, month_b):
                continue
            uebungen[satz.exercise_id] = satz.exercise
            saetze_je_uebung[satz.exercise_id][monat].append(satz)

        ergebnis = []
        for exercise_id, nach_monat in saetze_je_uebung.items():
            uebung = uebungen[exercise_id]
            a = _stats(nach_monat[month_a], weighted=uebung.weighted) if nach_monat[month_a] else None
            b = _stats(nach_monat[month_b], weighted=uebung.weighted) if nach_monat[month_b] else None
            ergebnis.append(
                ExerciseProgress(
                    exercise_id=exercise_id,
                    title=uebung.title,
                    weighted=uebung.weighted,
                    month_a=a,
                    month_b=b,
                    delta=ExerciseProgressDelta(
                        best_weight=_differenz(
                            a.best_weight if a else None, b.best_weight if b else None
                        ),
                        best_reps=_differenz(
                            a.best_reps if a else None, b.best_reps if b else None
                        ),
                        avg_reps=(
                            round(diff, 1)
                            if (diff := _differenz(a.avg_reps if a else None, b.avg_reps if b else None))
                            is not None
                            else None
                        ),
                        avg_weight=_differenz(
                            a.avg_weight if a else None, b.avg_weight if b else None
                        ),
                    ),
                )
            )

        # Alphabetisch: die Liste soll zwischen zwei Aufrufen gleich aussehen.
        ergebnis.sort(key=lambda e: e.title.lower())

        return ProgressComparison(
            month_a=month_a,
            month_b=month_b,
            label_a=_label(month_a),
            label_b=_label(month_b),
            exercises=ergebnis,
            excluded_custom_workouts=self._custom_count(user_id, (month_a, month_b)),
        )

    def _custom_count(self, user_id: int, monate: tuple[str, ...]) -> int:
        """Wie viele freie Trainings in den beiden Monaten uebergangen wurden.

        Damit kann das Frontend erklaeren, warum eine Einheit in der Historie
        steht, in der Auswertung aber fehlt.
        """
        return sum(
            1
            for workout in self.workout_repo.list_for_log(user_id, limit=1000)
            if workout.is_custom and month_key(workout.date) in monate
        )
