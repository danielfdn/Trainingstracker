"""Das Trainingslog - die zweite Haelfte der Spezifikation.

Zwei Ansichten:
  1. GET /users/{id}/log/workouts  - alle vergangenen Einheiten
  2. GET /users/{id}/log/progress  - Auswertung Monat gegen Monat

Dazu GET /users/{id}/log/months, das die beiden Dropdowns fuellt: es liefert
nur Monate, in denen wirklich trainiert wurde, sodass der User keinen leeren
Monat auswaehlen kann.
"""

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import TrainingLogServiceDep, UserRepoDep
from app.core.time import parse_month
from app.schemas.training_log import (
    MonthOption,
    ProgressComparison,
    WorkoutLogEntry,
)

router = APIRouter(prefix="/users", tags=["training-log"])


def _pruefe_user(user_id: int, repo: UserRepoDep) -> None:
    if repo.get(user_id) is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} nicht gefunden")


@router.get("/{user_id}/log/workouts", response_model=list[WorkoutLogEntry])
def read_log(
    user_id: int,
    service: TrainingLogServiceDep,
    user_repo: UserRepoDep,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
) -> list[WorkoutLogEntry]:
    """Ansicht 1: die Historie, neueste zuerst.

    Freie Trainings stehen mit drin und tragen den Typ "Custom" - nur aus
    der Auswertung bleiben sie heraus.
    """
    _pruefe_user(user_id, user_repo)
    return service.history(user_id, skip=skip, limit=limit)


@router.get("/{user_id}/log/months", response_model=list[MonthOption])
def read_months(
    user_id: int, service: TrainingLogServiceDep, user_repo: UserRepoDep
) -> list[MonthOption]:
    """Die Monate mit Einheiten, neueste zuerst - fuer die beiden Dropdowns."""
    _pruefe_user(user_id, user_repo)
    return service.months(user_id)


@router.get("/{user_id}/log/progress", response_model=ProgressComparison)
def read_progress(
    user_id: int,
    service: TrainingLogServiceDep,
    user_repo: UserRepoDep,
    month_a: str = Query(description="Monat im Format JJJJ-MM", examples=["2025-09"]),
    month_b: str = Query(description="Monat im Format JJJJ-MM", examples=["2026-04"]),
) -> ProgressComparison:
    """Ansicht 2: Fortschritt je Uebung, Monat A gegen Monat B.

    Beide Monate waehlt der User frei - auch weit auseinanderliegende, wie
    09/25 gegen 04/26. Genau dafuer haengen die Uebungen am User und nicht
    am Plan: sonst waeren es ueber einen Planwechsel hinweg zwei
    verschiedene Uebungen und es gaebe nichts zu vergleichen.
    """
    _pruefe_user(user_id, user_repo)
    for wert in (month_a, month_b):
        try:
            parse_month(wert)
        except ValueError as fehler:
            # 422, nicht 500: das ist eine Eingabe des Clients.
            raise HTTPException(status_code=422, detail=str(fehler)) from None
    return service.compare(user_id, month_a, month_b)
