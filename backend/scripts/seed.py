"""Legt Beispieldaten in der Datenbank an (Entwicklung, nicht Produktion).

Aufruf aus dem Ordner backend/:
    uv run python -m scripts.seed

Das Skript ist wiederholbar: Es loescht vorher genau die User aus SEED_USERS
und legt sie neu an. Durch die Cascade-Beziehungen verschwinden dabei auch
deren Plaene, Uebungen, Workouts und Saetze. Daten, die nicht von diesem
Skript stammen, bleiben unangetastet.

Datenmodell-Hinweis: Ein Satz haengt an einer Uebung UND an einem Workout.
Er beschreibt also nicht die Planvorgabe, sondern was an einem konkreten Tag
tatsaechlich gemacht wurde. Deshalb entstehen die Saetze hier immer aus einem
Workout heraus.
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.core.db import SessionLocal
from app.entities import Exercise, Set, User, Workout, WorkoutPlan

# Namen, die dieses Skript verwaltet - dienen zugleich als Wiedererkennung
# beim erneuten Lauf.
SEED_USERS = ["Seed Anna", "Seed Ben", "Seed Clara"]

# Kalendertag als Bezugspunkt, damit die Workouts immer "kuerzlich" wirken.
TODAY = date.today()


def _dt(days_ago: int, hour: int = 18) -> datetime:
    """Zeitpunkt vor n Tagen, als aware datetime (die Spalte ist timezone=True)."""
    day = TODAY - timedelta(days=days_ago)
    return datetime(day.year, day.month, day.day, hour, tzinfo=timezone.utc)


def _zeiten(days_ago: int, minuten: int, hour: int = 18) -> dict:
    """Start-/Endzeit einer abgeschlossenen Einheit mit gegebener Dauer."""
    start = _dt(days_ago, hour)
    return {"started_at": start, "finished_at": start + timedelta(minutes=minuten)}


def clear(session) -> int:
    """Entfernt die vom Skript angelegten User samt allem, was daran haengt."""
    users = session.scalars(select(User).where(User.name.in_(SEED_USERS))).all()
    for user in users:
        session.delete(user)
    session.commit()
    return len(users)


def seed(session) -> None:
    # --- User 1: Ganzkoerperplan mit Verlauf ueber vier Wochen ------------
    anna = User(name="Seed Anna", age=27, weight=64.5)
    anna_plan = WorkoutPlan(
        title="Ganzkoerper 3er-Split",
        training_days=3,
        starting_date=TODAY - timedelta(days=28),
        ending_date=TODAY + timedelta(days=56),
    )
    kniebeuge = Exercise(title="Kniebeuge", weighted=True)
    bank = Exercise(title="Bankdruecken", weighted=True)
    klimmzug = Exercise(title="Klimmzuege", weighted=False)
    anna_plan.exercises = [kniebeuge, bank, klimmzug]

    # Drei absolvierte Einheiten mit steigenden Gewichten - daraus laesst
    # sich im Frontend ein Verlauf zeichnen.
    for days_ago, squat, bench, pullups, minuten, comment in [
        (21, 60.0, 35.0, 5, 72, "Erster Tag, Technik geuebt"),
        (14, 65.0, 37.5, 6, 65, "Kniebeuge +5 kg"),
        (2, 70.0, 40.0, 7, 58, "Gut gelaufen"),
    ]:
        einheit = Workout(
            date=_dt(days_ago),
            attended=True,
            comment=comment,
            **_zeiten(days_ago, minuten),
        )
        einheit.sets = [
            Set(exercise=kniebeuge, repetitions=8, weight=squat),
            Set(exercise=kniebeuge, repetitions=8, weight=squat),
            Set(exercise=kniebeuge, repetitions=6, weight=squat + 5),
            Set(exercise=bank, repetitions=10, weight=bench),
            Set(exercise=bank, repetitions=8, weight=bench + 2.5),
            Set(exercise=klimmzug, repetitions=pullups, weight=None),
            Set(exercise=klimmzug, repetitions=pullups - 1, weight=None),
        ]
        anna_plan.workouts.append(einheit)

    # Eine ausgefallene Einheit - ohne Saetze, weil nichts stattgefunden hat.
    anna_plan.workouts.append(
        Workout(date=_dt(7), attended=False, comment="Krank ausgefallen")
    )
    anna.workout_plans = [anna_plan]

    # --- User 2: abgeschlossener alter Plan + laufender neuer Plan --------
    ben = User(name="Seed Ben", age=34, weight=82.0)

    ben_old = WorkoutPlan(
        title="Grundlagenaufbau",
        training_days=2,
        starting_date=TODAY - timedelta(days=180),
        ending_date=TODAY - timedelta(days=90),
    )
    rudern = Exercise(title="Rudern am Kabelzug", weighted=True)
    ben_old.exercises = [rudern]
    for days_ago, gewicht, minuten in [(150, 40.0, 45), (120, 45.0, 50)]:
        einheit = Workout(
            date=_dt(days_ago),
            attended=True,
            comment="",
            **_zeiten(days_ago, minuten),
        )
        einheit.sets = [
            Set(exercise=rudern, repetitions=12, weight=gewicht),
            Set(exercise=rudern, repetitions=12, weight=gewicht),
        ]
        ben_old.workouts.append(einheit)

    ben_new = WorkoutPlan(
        title="Push/Pull/Legs",
        training_days=4,
        starting_date=TODAY - timedelta(days=10),
        ending_date=None,
    )
    kreuzheben = Exercise(title="Kreuzheben", weighted=True)
    schulter = Exercise(title="Schulterdruecken", weighted=True)
    liegestuetz = Exercise(title="Liegestuetze", weighted=False)
    beinpresse = Exercise(title="Beinpresse", weighted=True)
    ben_new.exercises = [kreuzheben, schulter, liegestuetz, beinpresse]

    w1 = Workout(date=_dt(8), attended=True, comment="Einstieg", **_zeiten(8, 55))
    w1.sets = [
        Set(exercise=kreuzheben, repetitions=5, weight=100.0),
        Set(exercise=kreuzheben, repetitions=5, weight=105.0),
        Set(exercise=schulter, repetitions=10, weight=30.0),
    ]
    w2 = Workout(date=_dt(5), attended=True, comment="", **_zeiten(5, 41))
    w2.sets = [
        Set(exercise=liegestuetz, repetitions=20, weight=None),
        Set(exercise=liegestuetz, repetitions=18, weight=None),
        Set(exercise=beinpresse, repetitions=12, weight=140.0),
    ]
    # Bewusst ohne finished_at: deckt den Zustand "laeuft gerade" ab, den das
    # Frontend mit laufender Uhr darstellen muss. Der Start liegt absichtlich
    # nur wenige Minuten zurueck - laege er weiter als MAX_WORKOUT_HOURS
    # zurueck, wuerde die Einheit beim ersten Lesen automatisch geschlossen.
    w3 = Workout(
        date=_dt(0),
        attended=True,
        comment="Kreuzheben PR bei 120 kg",
        started_at=datetime.now(timezone.utc) - timedelta(minutes=40),
    )
    w3.sets = [
        Set(exercise=kreuzheben, repetitions=5, weight=110.0),
        Set(exercise=kreuzheben, repetitions=3, weight=120.0),
        Set(exercise=schulter, repetitions=8, weight=32.5),
    ]
    ben_new.workouts = [w1, w2, w3]
    ben.workout_plans = [ben_old, ben_new]

    # --- User 3: frisch angelegter Plan, noch kein einziges Training ------
    # Bewusst ohne Workouts - damit deckt der Seed auch den Leerfall ab,
    # den das Frontend anzeigen koennen muss.
    clara = User(name="Seed Clara", age=41, weight=58.0)
    clara_plan = WorkoutPlan(
        title="Einstieg Koerpergewicht",
        training_days=2,
        starting_date=TODAY,
        ending_date=None,
    )
    clara_plan.exercises = [
        Exercise(title="Kniebeuge ohne Gewicht", weighted=False),
        Exercise(title="Plank (Sekunden als Wiederholungen)", weighted=False),
    ]
    clara.workout_plans = [clara_plan]

    session.add_all([anna, ben, clara])
    session.commit()


def main() -> None:
    with SessionLocal() as session:
        removed = clear(session)
        if removed:
            print(f"{removed} vorhandene Seed-User entfernt")
        seed(session)
        print("Beispieldaten angelegt:")
        for user in session.scalars(
            select(User).where(User.name.in_(SEED_USERS)).order_by(User.id)
        ):
            print(f"  User {user.id}: {user.name}")
            for plan in user.workout_plans:
                sets_total = sum(len(w.sets) for w in plan.workouts)
                dauern = [
                    w.duration_seconds // 60
                    for w in plan.workouts
                    if w.duration_seconds is not None
                ]
                dauer_text = f", Dauer {'/'.join(map(str, dauern))} min" if dauern else ""
                print(
                    f"    Plan {plan.id}: {plan.title} "
                    f"({len(plan.exercises)} Uebungen, "
                    f"{len(plan.workouts)} Workouts, {sets_total} Saetze{dauer_text})"
                )


if __name__ == "__main__":
    main()
