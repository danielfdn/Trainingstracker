from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import (
    ExerciseRepoDep,
    TrainingDayRepoDep,
    UserRepoDep,
    WorkoutPlanRepoDep,
    WorkoutRepoDep,
)
from app.core.config import settings
from app.core.time import as_utc
from app.entities.set import Set
from app.entities.workout import Workout
from app.schemas.workout import (
    WorkoutCreate,
    WorkoutPublic,
    WorkoutSync,
    WorkoutUpdate,
    WorkoutWithSets,
)

router = APIRouter(prefix="/workouts", tags=["workouts"])

MAX_DAUER = timedelta(hours=settings.MAX_WORKOUT_HOURS)


def _vergessene_schliessen(repo) -> None:
    """Raeumt vergessene Einheiten auf, bevor gelesen oder gestartet wird.

    Kein Hintergrundjob noetig: Es genuegt, im Moment des Zugriffs
    aufzuraeumen - vorher sieht ohnehin niemand das Ergebnis.
    """
    repo.auto_close_stale(MAX_DAUER)


def _koerpergewicht(plan, user_repo) -> float | None:
    """Das aktuelle Profilgewicht - eingefroren fuer diese eine Einheit.

    Der User traegt es nirgends ein: es steht ohnehin im Profil, und dort
    aendert er es, wenn es sich aendert. Aendern wirkt sich nur auf kuenftige
    Einheiten aus, denn hier ist es dann schon kopiert.
    """
    user = user_repo.get(plan.user_id)
    return user.weight if user is not None else None


@router.post("", response_model=WorkoutPublic, status_code=status.HTTP_201_CREATED)
def create_workout(
    workout_in: WorkoutCreate,
    repo: WorkoutRepoDep,
    plan_repo: WorkoutPlanRepoDep,
    day_repo: TrainingDayRepoDep,
    user_repo: UserRepoDep,
) -> Workout:
    """Legt eine Einheit an.

    Mit training_day_id wird ein geplanter Tag trainiert ("Push"), ohne sie
    ein freies Training - z.B. wenn im Hotel die Geraete fehlen. Freie
    Einheiten stehen in der Historie, zaehlen aber nicht in die Auswertung.
    """
    plan = plan_repo.get(workout_in.workout_plan_id)
    if plan is None:
        raise HTTPException(
            status_code=404,
            detail=f"Trainingsplan {workout_in.workout_plan_id} nicht gefunden",
        )
    if workout_in.training_day_id is not None:
        tag = day_repo.get(workout_in.training_day_id)
        if tag is None:
            raise HTTPException(
                status_code=404,
                detail=f"Trainingstag {workout_in.training_day_id} nicht gefunden",
            )
        # Sonst koennte eine Einheit von Plan A den "Push"-Tag aus Plan B
        # tragen - die Auswertung wuerde die Einheit dem falschen Plan zuordnen.
        if tag.workout_plan_id != workout_in.workout_plan_id:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Trainingstag {tag.id} gehoert zu Plan {tag.workout_plan_id}, "
                    f"die Einheit aber zu Plan {workout_in.workout_plan_id}"
                ),
            )
    return repo.create(
        Workout(**workout_in.model_dump(), body_weight=_koerpergewicht(plan, user_repo))
    )


@router.post(
    "/sync",
    response_model=WorkoutWithSets,
    status_code=status.HTTP_201_CREATED,
)
def sync_workout(
    einheit: WorkoutSync,
    antwort: Response,
    repo: WorkoutRepoDep,
    plan_repo: WorkoutPlanRepoDep,
    day_repo: TrainingDayRepoDep,
    exercise_repo: ExerciseRepoDep,
    user_repo: UserRepoDep,
) -> Workout:
    """Nimmt eine offline erfasste Einheit samt Saetzen in einem Aufruf an.

    Gedacht fuer den Trainingsbildschirm: die Saetze werden waehrend des
    Trainings lokal gespeichert und erst beim Abschluss uebertragen. Im Keller
    ohne Empfang geht dabei nichts verloren, und ein Absturz des Browsers
    ebenfalls nicht - die Saetze standen nie nur im Arbeitsspeicher.

    Idempotent ueber client_uuid: ein wiederholter Aufruf liefert die
    vorhandene Einheit mit 200 zurueck, statt sie ein zweites Mal anzulegen.
    """
    vorhanden = repo.get_by_client_uuid(einheit.client_uuid)
    if vorhanden is not None:
        # Kein Fehler: aus Sicht des Handys ist genau das der Erfolgsfall,
        # nur eben schon beim ersten Versuch passiert.
        antwort.status_code = status.HTTP_200_OK
        return vorhanden

    plan = plan_repo.get(einheit.workout_plan_id)
    if plan is None:
        raise HTTPException(
            status_code=404,
            detail=f"Trainingsplan {einheit.workout_plan_id} nicht gefunden",
        )
    if einheit.training_day_id is not None:
        tag = day_repo.get(einheit.training_day_id)
        if tag is None:
            raise HTTPException(
                status_code=404,
                detail=f"Trainingstag {einheit.training_day_id} nicht gefunden",
            )
        if tag.workout_plan_id != einheit.workout_plan_id:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Trainingstag {tag.id} gehoert zu Plan {tag.workout_plan_id}, "
                    f"die Einheit aber zu Plan {einheit.workout_plan_id}"
                ),
            )

    # Die Plaetze des Trainingstages, um die Satz-Zuordnung zu pruefen.
    # Ein Satz darf nur auf einen Platz zeigen, der zu genau diesem Tag
    # gehoert und dieselbe Uebung traegt - sonst stuende in der Historie
    # "Bankdruecken" unter dem Platz "Kniebeuge".
    plaetze = {}
    if einheit.training_day_id is not None:
        tag_mit_uebungen = day_repo.get_with_exercises(einheit.training_day_id)
        if tag_mit_uebungen is not None:
            plaetze = {link.id: link for link in tag_mit_uebungen.exercise_links}

    workout = Workout(
        date=einheit.date,
        # Wer eine Einheit uebertraegt, hat sie absolviert.
        attended=True,
        comment=einheit.comment,
        started_at=einheit.started_at,
        finished_at=einheit.finished_at,
        workout_plan_id=einheit.workout_plan_id,
        training_day_id=einheit.training_day_id,
        client_uuid=einheit.client_uuid,
        body_weight=_koerpergewicht(plan, user_repo),
    )

    for satz in einheit.sets:
        uebung = exercise_repo.get(satz.exercise_id)
        if uebung is None:
            raise HTTPException(
                status_code=404, detail=f"Uebung {satz.exercise_id} nicht gefunden"
            )
        if uebung.user_id != plan.user_id:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Uebung '{uebung.title}' gehoert zu User {uebung.user_id}, "
                    f"das Workout aber zu User {plan.user_id}"
                ),
            )
        # Dieselbe Fachregel wie in POST /sets - eine Uebung ohne
        # Zusatzgewicht darf kein Gewicht tragen.
        if not uebung.weighted and satz.weight is not None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Uebung '{uebung.title}' ist nicht gewichtsbasiert - "
                    "weight muss leer bleiben"
                ),
            )
        if satz.training_day_exercise_id is not None:
            platz = plaetze.get(satz.training_day_exercise_id)
            if platz is None:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Platz {satz.training_day_exercise_id} gehoert nicht "
                        f"zu Trainingstag {einheit.training_day_id}"
                    ),
                )
            if platz.exercise_id != satz.exercise_id:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Platz {platz.id} traegt Uebung {platz.exercise_id}, "
                        f"der Satz aber Uebung {satz.exercise_id}"
                    ),
                )
        workout.sets.append(
            Set(
                exercise_id=satz.exercise_id,
                repetitions=satz.repetitions,
                weight=satz.weight,
                training_day_exercise_id=satz.training_day_exercise_id,
            )
        )

    # Ein einziges commit fuer Einheit und Saetze: entweder die ganze
    # Trainingseinheit steht in der Datenbank, oder gar nichts davon.
    return repo.create(workout)


@router.get("", response_model=list[WorkoutPublic])
def read_workouts(
    repo: WorkoutRepoDep,
    workout_plan_id: int | None = None,
    user_id: int | None = None,
    since: datetime | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Workout]:
    """Trainingshistorie - filterbar nach Plan oder User, optional ab einem Datum."""
    _vergessene_schliessen(repo)
    if workout_plan_id is not None:
        return repo.list_by_plan(workout_plan_id, skip=skip, limit=limit)
    if user_id is not None:
        return repo.list_by_user(user_id, since=since, skip=skip, limit=limit)
    return repo.list(skip=skip, limit=limit)


@router.get("/{workout_id}", response_model=WorkoutWithSets)
def read_workout(workout_id: int, repo: WorkoutRepoDep) -> Workout:
    """Detailansicht: die Einheit mit allen darin protokollierten Saetzen."""
    _vergessene_schliessen(repo)
    workout = repo.get_with_sets(workout_id)
    if workout is None:
        raise HTTPException(
            status_code=404, detail=f"Workout {workout_id} nicht gefunden"
        )
    return workout


@router.patch("/{workout_id}", response_model=WorkoutPublic)
def update_workout(
    workout_id: int, workout_in: WorkoutUpdate, repo: WorkoutRepoDep
) -> Workout:
    workout = repo.get(workout_id)
    if workout is None:
        raise HTTPException(
            status_code=404, detail=f"Workout {workout_id} nicht gefunden"
        )
    daten = workout_in.model_dump(exclude_unset=True)

    # Ein PATCH kann nur eine der beiden Zeiten schicken. Geprueft wird
    # deshalb der Zustand, der nach dem Speichern gelten wuerde.
    # as_utc, weil der gespeicherte Wert je nach DB naiv sein kann, der
    # frisch geschickte aber immer eine Zeitzone traegt.
    start = as_utc(daten.get("started_at", workout.started_at))
    ende = as_utc(daten.get("finished_at", workout.finished_at))
    if ende is not None:
        if start is None:
            raise HTTPException(
                status_code=422,
                detail="finished_at ohne started_at - eine Einheit kann nicht enden, ohne begonnen zu haben",
            )
        if ende < start:
            raise HTTPException(
                status_code=422, detail="finished_at darf nicht vor started_at liegen"
            )

    return repo.update(workout, daten)


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(workout_id: int, repo: WorkoutRepoDep) -> None:
    workout = repo.get(workout_id)
    if workout is None:
        raise HTTPException(
            status_code=404, detail=f"Workout {workout_id} nicht gefunden"
        )
    repo.delete(workout)


@router.post("/{workout_id}/start", response_model=WorkoutPublic)
def start_workout(workout_id: int, repo: WorkoutRepoDep) -> Workout:
    """Startet die Einheit und laesst die Uhr laufen.

    Der Zeitstempel kommt vom Server, nicht vom Client - sonst haengt die
    gemessene Dauer davon ab, wie richtig die Uhr des Handys geht.
    """
    _vergessene_schliessen(repo)
    workout = repo.get(workout_id)
    if workout is None:
        raise HTTPException(
            status_code=404, detail=f"Workout {workout_id} nicht gefunden"
        )
    if workout.started_at is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Workout {workout_id} wurde bereits um {workout.started_at.isoformat()} gestartet",
        )
    # Wer startet, war da - das erspart dem Frontend einen zweiten Aufruf.
    return repo.update(
        workout, {"started_at": datetime.now(timezone.utc), "attended": True}
    )


@router.post("/{workout_id}/finish", response_model=WorkoutPublic)
def finish_workout(workout_id: int, repo: WorkoutRepoDep) -> Workout:
    """Beendet die laufende Einheit. Die Dauer ergibt sich aus der Differenz."""
    _vergessene_schliessen(repo)
    workout = repo.get(workout_id)
    if workout is None:
        raise HTTPException(
            status_code=404, detail=f"Workout {workout_id} nicht gefunden"
        )
    if workout.started_at is None:
        raise HTTPException(
            status_code=409,
            detail=f"Workout {workout_id} wurde nie gestartet - erst /start aufrufen",
        )
    if workout.finished_at is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Workout {workout_id} ist bereits seit {workout.finished_at.isoformat()} beendet",
        )
    return repo.update(workout, {"finished_at": datetime.now(timezone.utc)})
