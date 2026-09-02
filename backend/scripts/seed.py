"""Legt Beispieldaten in der Datenbank an (Entwicklung, nicht Produktion).

Aufruf aus dem Ordner backend/:
    uv run python -m scripts.seed

Das Skript ist wiederholbar: Es loescht vorher genau die User aus SEED_USERS
und legt sie neu an. Durch die Cascade-Beziehungen verschwinden dabei auch
deren Katalog, Plaene, Trainingstage, Workouts und Saetze. Daten, die nicht
von diesem Skript stammen, bleiben unangetastet.

Datenmodell-Hinweise:
  - Eine Uebung gehoert dem USER, nicht dem Plan. Nur deshalb laesst sich der
    Verlauf ueber einen Planwechsel hinweg vergleichen.
  - Ein Satz haengt an einer Uebung UND an einem Workout. Er beschreibt also
    nicht die Vorgabe, sondern was an einem konkreten Tag gemacht wurde.
  - Die Vorgabe ("3x8-10") steht in TrainingDayExercise.
  - Ein Workout ohne training_day_id ist ein freies Training ("Custom").

Die Daten sind bewusst ueber mehrere Monate verteilt, damit der
Monatsvergleich der Auswertung etwas zu vergleichen hat.
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.core.db import SessionLocal
from app.entities import (
    Exercise,
    Set,
    TrainingDay,
    TrainingDayExercise,
    User,
    Workout,
    WorkoutPlan,
)

# Namen, die dieses Skript verwaltet - dienen zugleich als Wiedererkennung
# beim erneuten Lauf.
SEED_USERS = ["Seed Anna", "Seed Ben", "Seed Clara"]

# Kalendertag als Bezugspunkt, damit die Workouts immer "kuerzlich" wirken.
TODAY = date.today()


def _monat(vor_monaten: int) -> date:
    """Der Erste des Monats, der n Monate zurueckliegt.

    Monate sind Kalendermonate und beginnen immer am Ersten - genau so
    schneidet die Auswertung sie spaeter zu.
    """
    monat_index = TODAY.year * 12 + (TODAY.month - 1) - vor_monaten
    return date(monat_index // 12, monat_index % 12 + 1, 1)


def _dt(tag: date, hour: int = 18) -> datetime:
    """Zeitpunkt als aware datetime (die Spalte ist timezone=True)."""
    return datetime(tag.year, tag.month, tag.day, hour, tzinfo=timezone.utc)


def _einheit(
    tag: date, minuten: int, *, training_day: TrainingDay | None = None, comment: str = ""
) -> Workout:
    """Eine abgeschlossene Einheit mit gegebener Dauer.

    training_day=None ergibt ein freies Training ("Custom").
    """
    start = _dt(tag)
    return Workout(
        date=start,
        attended=True,
        comment=comment,
        started_at=start,
        finished_at=start + timedelta(minutes=minuten),
        training_day=training_day,
    )


def clear(session) -> int:
    """Entfernt die vom Skript angelegten User samt allem, was daran haengt."""
    users = session.scalars(select(User).where(User.name.in_(SEED_USERS))).all()
    for user in users:
        # Erst die Auswahl loesen: appuser zeigt auf workout_plan und
        # umgekehrt - ohne das haenge der Fremdschluessel beim Loeschen.
        user.active_workout_plan_id = None
    session.flush()
    for user in users:
        session.delete(user)
    session.commit()
    return len(users)


def seed(session) -> None:
    # --- User 1: durchgehender Verlauf ueber fuenf Monate -----------------
    # Der interessante Fall fuer die Auswertung: dieselbe Uebung, viele
    # Monate, steigende Gewichte.
    anna = User(name="Seed Anna", age=27, weight=64.5)

    kniebeuge = Exercise(title="Kniebeuge", weighted=True)
    bank = Exercise(title="Bankdruecken", weighted=True)
    klimmzug = Exercise(title="Klimmzuege", weighted=False)
    rudern = Exercise(title="Rudern am Kabelzug", weighted=True)
    anna.exercises = [kniebeuge, bank, klimmzug, rudern]

    anna_plan = WorkoutPlan(
        title="Push/Pull/Legs",
        starting_date=_monat(5),
        ending_date=None,
    )
    push = TrainingDay(position=1, workout_type="Push")
    push.exercise_links = [
        TrainingDayExercise(
            exercise=bank, position=1, target_sets=3, target_reps_min=8, target_reps_max=10
        ),
    ]
    pull = TrainingDay(position=2, workout_type="Pull")
    pull.exercise_links = [
        TrainingDayExercise(
            exercise=klimmzug, position=1, target_sets=3, target_reps_min=5, target_reps_max=8
        ),
        TrainingDayExercise(
            exercise=rudern, position=2, target_sets=3, target_reps_min=10, target_reps_max=12
        ),
    ]
    legs = TrainingDay(position=3, workout_type="Legs")
    legs.exercise_links = [
        TrainingDayExercise(
            exercise=kniebeuge, position=1, target_sets=4, target_reps_min=5, target_reps_max=8
        ),
    ]
    anna_plan.training_days = [push, pull, legs]

    # Fuenf Monate Verlauf: pro Monat ein Push- und ein Legs-Tag, mit
    # steigenden Gewichten. Damit hat der Vergleich "Monat A gegen Monat B"
    # in jedem Monat Zahlen.
    for vor_monaten in range(5, -1, -1):
        fortschritt = 5 - vor_monaten
        monatsanfang = _monat(vor_monaten)

        push_tag = monatsanfang + timedelta(days=3)
        legs_tag = monatsanfang + timedelta(days=10)
        pull_tag = monatsanfang + timedelta(days=17)
        # Der laufende Monat ist noch nicht vorbei - keine Termine in der Zukunft.
        if push_tag > TODAY:
            continue

        push_einheit = _einheit(push_tag, 58, training_day=push)
        push_einheit.sets = [
            Set(exercise=bank, repetitions=10, weight=35.0 + fortschritt * 2.5),
            Set(exercise=bank, repetitions=9, weight=35.0 + fortschritt * 2.5),
            Set(exercise=bank, repetitions=8, weight=37.5 + fortschritt * 2.5),
        ]
        anna_plan.workouts.append(push_einheit)

        if legs_tag <= TODAY:
            legs_einheit = _einheit(legs_tag, 65, training_day=legs)
            legs_einheit.sets = [
                Set(exercise=kniebeuge, repetitions=8, weight=60.0 + fortschritt * 5),
                Set(exercise=kniebeuge, repetitions=8, weight=60.0 + fortschritt * 5),
                Set(exercise=kniebeuge, repetitions=6, weight=65.0 + fortschritt * 5),
            ]
            anna_plan.workouts.append(legs_einheit)

        if pull_tag <= TODAY:
            pull_einheit = _einheit(pull_tag, 52, training_day=pull)
            pull_einheit.sets = [
                Set(exercise=klimmzug, repetitions=5 + fortschritt, weight=None),
                Set(exercise=klimmzug, repetitions=4 + fortschritt, weight=None),
                Set(exercise=rudern, repetitions=12, weight=40.0 + fortschritt * 2.5),
            ]
            anna_plan.workouts.append(pull_einheit)

    # Ein freies Training: im Urlaub fehlten die Geraete. Steht in der
    # Historie, faellt aber aus der Auswertung heraus.
    custom = _einheit(
        _monat(1) + timedelta(days=22),
        35,
        comment="Hotel ohne Langhantel - improvisiert",
    )
    custom.sets = [
        Set(exercise=klimmzug, repetitions=8, weight=None),
        Set(exercise=klimmzug, repetitions=7, weight=None),
    ]
    anna_plan.workouts.append(custom)

    # Eine ausgefallene Einheit - ohne Saetze, weil nichts stattgefunden hat.
    anna_plan.workouts.append(
        Workout(
            date=_dt(TODAY - timedelta(days=5)),
            attended=False,
            comment="Krank ausgefallen",
            training_day=push,
        )
    )
    anna.workout_plans = [anna_plan]

    # --- User 2: Planwechsel bei gleichem Uebungskatalog ------------------
    # Genau der Fall, fuer den die Uebungen am User haengen: Bankdruecken
    # kommt in beiden Plaenen vor und bleibt dieselbe Uebung, sodass sich
    # 09/25 mit 04/26 vergleichen laesst.
    ben = User(name="Seed Ben", age=34, weight=82.0)
    ben_bank = Exercise(title="Bankdruecken", weighted=True)
    ben_kreuzheben = Exercise(title="Kreuzheben", weighted=True)
    ben_schulter = Exercise(title="Schulterdruecken", weighted=True)
    ben_liegestuetz = Exercise(title="Liegestuetze", weighted=False)
    ben.exercises = [ben_bank, ben_kreuzheben, ben_schulter, ben_liegestuetz]

    ben_alt = WorkoutPlan(
        title="Grundlagenaufbau",
        starting_date=_monat(11),
        ending_date=_monat(7),
    )
    alt_tag = TrainingDay(position=1, workout_type="Ganzkoerper")
    alt_tag.exercise_links = [
        TrainingDayExercise(exercise=ben_bank, position=1, target_sets=3, target_reps_min=10, target_reps_max=12),
        TrainingDayExercise(exercise=ben_kreuzheben, position=2, target_sets=3, target_reps_min=5, target_reps_max=5),
    ]
    ben_alt.training_days = [alt_tag]
    for vor_monaten in (10, 9, 8):
        tag = _monat(vor_monaten) + timedelta(days=6)
        einheit = _einheit(tag, 48, training_day=alt_tag)
        einheit.sets = [
            Set(exercise=ben_bank, repetitions=12, weight=60.0),
            Set(exercise=ben_bank, repetitions=10, weight=62.5),
            Set(exercise=ben_kreuzheben, repetitions=5, weight=100.0),
        ]
        ben_alt.workouts.append(einheit)

    ben_neu = WorkoutPlan(
        title="Oberkoerper/Unterkoerper",
        starting_date=_monat(2),
        ending_date=None,
    )
    ober = TrainingDay(position=1, workout_type="Oberkoerper")
    ober.exercise_links = [
        TrainingDayExercise(exercise=ben_bank, position=1, target_sets=4, target_reps_min=6, target_reps_max=8),
        TrainingDayExercise(exercise=ben_schulter, position=2, target_sets=3, target_reps_min=8, target_reps_max=10),
        TrainingDayExercise(exercise=ben_liegestuetz, position=3, target_sets=3, target_reps_min=15, target_reps_max=20),
    ]
    unter = TrainingDay(position=2, workout_type="Unterkoerper")
    unter.exercise_links = [
        TrainingDayExercise(exercise=ben_kreuzheben, position=1, target_sets=4, target_reps_min=3, target_reps_max=5),
    ]
    ben_neu.training_days = [ober, unter]
    for vor_monaten in (2, 1):
        tag = _monat(vor_monaten) + timedelta(days=8)
        einheit = _einheit(tag, 55, training_day=ober)
        einheit.sets = [
            # Dieselbe Uebung wie im alten Plan, deutlich schwerer - der
            # Vergleich alt gegen neu ist der Kern der Auswertung.
            Set(exercise=ben_bank, repetitions=8, weight=75.0 + (2 - vor_monaten) * 5),
            Set(exercise=ben_bank, repetitions=6, weight=80.0 + (2 - vor_monaten) * 5),
            Set(exercise=ben_schulter, repetitions=10, weight=32.5),
            Set(exercise=ben_liegestuetz, repetitions=20, weight=None),
        ]
        ben_neu.workouts.append(einheit)

    # Bewusst ohne finished_at: deckt den Zustand "laeuft gerade" ab, den das
    # Frontend mit laufender Uhr darstellen muss. Der Start liegt absichtlich
    # nur wenige Minuten zurueck - laege er weiter als MAX_WORKOUT_HOURS
    # zurueck, wuerde die Einheit beim ersten Lesen automatisch geschlossen.
    laufend = Workout(
        date=_dt(TODAY),
        attended=True,
        comment="Laeuft gerade",
        started_at=datetime.now(timezone.utc) - timedelta(minutes=40),
        training_day=unter,
    )
    laufend.sets = [
        Set(exercise=ben_kreuzheben, repetitions=5, weight=110.0),
        Set(exercise=ben_kreuzheben, repetitions=3, weight=120.0),
    ]
    ben_neu.workouts.append(laufend)
    ben.workout_plans = [ben_alt, ben_neu]

    # --- User 3: frisch angelegter Plan, noch kein einziges Training ------
    # Bewusst ohne Workouts - damit deckt der Seed auch den Leerfall ab,
    # den das Frontend anzeigen koennen muss.
    clara = User(name="Seed Clara", age=41, weight=58.0)
    clara_kniebeuge = Exercise(title="Kniebeuge ohne Gewicht", weighted=False)
    clara_plank = Exercise(title="Plank (Sekunden als Wiederholungen)", weighted=False)
    clara.exercises = [clara_kniebeuge, clara_plank]
    clara_plan = WorkoutPlan(
        title="Einstieg Koerpergewicht", starting_date=TODAY, ending_date=None
    )
    clara_tag = TrainingDay(position=1, workout_type="Ganzkoerper")
    clara_tag.exercise_links = [
        TrainingDayExercise(exercise=clara_kniebeuge, position=1, target_sets=3, target_reps_min=15, target_reps_max=20),
        TrainingDayExercise(exercise=clara_plank, position=2, target_sets=3, target_reps_min=30, target_reps_max=45),
    ]
    clara_plan.training_days = [clara_tag]
    clara.workout_plans = [clara_plan]

    session.add_all([anna, ben, clara])
    session.flush()

    # Der aktive Plan wird erst nach dem flush gesetzt - vorher haben die
    # Plaene noch keine id.
    anna.active_workout_plan_id = anna_plan.id
    ben.active_workout_plan_id = ben_neu.id
    clara.active_workout_plan_id = clara_plan.id
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
            print(f"  User {user.id}: {user.name} ({len(user.exercises)} Uebungen im Katalog)")
            for plan in user.workout_plans:
                aktiv = " [aktiv]" if plan.id == user.active_workout_plan_id else ""
                sets_total = sum(len(w.sets) for w in plan.workouts)
                custom = sum(1 for w in plan.workouts if w.is_custom)
                custom_text = f", davon {custom} custom" if custom else ""
                print(
                    f"    Plan {plan.id}: {plan.title}{aktiv} "
                    f"({plan.training_days_per_week} Trainingstage, "
                    f"{len(plan.workouts)} Workouts{custom_text}, {sets_total} Saetze)"
                )


if __name__ == "__main__":
    main()
