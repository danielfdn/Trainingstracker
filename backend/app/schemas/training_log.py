"""Schemas des Trainingslogs.

Zwei Ansichten, wie in der Spezifikation beschrieben:
  1. Alle vergangenen Einheiten (WorkoutLogEntry)
  2. Auswertung: Monat gegen Monat, pro Uebung (ProgressComparison)
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

CUSTOM_LABEL = "Custom"


class WorkoutLogEntry(BaseModel):
    """Eine Zeile der Historie."""

    id: int
    date: datetime
    attended: bool
    comment: str
    # "Push", "Pull" - oder "Custom" beim freien Training.
    workout_type: str
    is_custom: bool
    plan_title: str
    duration_seconds: int | None = None
    duration: str | None = None
    set_count: int
    exercise_count: int


class MonthOption(BaseModel):
    """Ein Monat, in dem tatsaechlich trainiert wurde.

    Fuellt die beiden Dropdowns der Auswertung - so kann der User keinen
    leeren Monat waehlen.
    """

    month: str = Field(examples=["2026-04"])
    label: str = Field(examples=["04/2026"])
    workout_count: int


class ExerciseMonthStats(BaseModel):
    """Die Zahlen einer Uebung in einem Monat."""

    # Kennzahl der Auswertung: das schwerste Gewicht des Monats.
    # None bei Koerpergewichtsuebungen - dort zaehlen die Wiederholungen.
    best_weight: Decimal | None = None
    # Bester Satz nach Wiederholungen - fuer Klimmzuege & Co. die
    # eigentliche Fortschrittszahl.
    best_reps: int | None = None
    avg_reps: float | None = None
    avg_weight: Decimal | None = None
    set_count: int = 0
    session_count: int = 0


class ExerciseProgressDelta(BaseModel):
    """Differenz B minus A. None, wenn eine Seite fehlt."""

    best_weight: Decimal | None = None
    best_reps: int | None = None
    avg_reps: float | None = None
    avg_weight: Decimal | None = None


class ExerciseProgress(BaseModel):
    exercise_id: int
    title: str
    weighted: bool
    month_a: ExerciseMonthStats | None = None
    month_b: ExerciseMonthStats | None = None
    delta: ExerciseProgressDelta


class ProgressComparison(BaseModel):
    """Auswertung zweier Monate, z.B. 09/25 gegen 04/26."""

    month_a: str
    month_b: str
    label_a: str
    label_b: str
    # Uebungen, die in mindestens einem der beiden Monate vorkamen.
    exercises: list[ExerciseProgress]
    # Freie Trainings zaehlen nicht mit - das Frontend kann den Hinweis zeigen.
    excluded_custom_workouts: int = 0
