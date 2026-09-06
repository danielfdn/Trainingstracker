"""Tests der Backend-Vorarbeiten fuer Phase 4.

Drei Themen: das Koerpergewicht je Einheit, die Offline-Synchronisation und
das Kopieren eines Plans.
"""

from fastapi.testclient import TestClient

from tests.test_api import (
    _create_exercise,
    _create_plan,
    _create_training_day,
    _create_user,
)

# --- Koerpergewicht je Einheit -------------------------------------------


def test_einheit_uebernimmt_koerpergewicht_aus_dem_profil(client: TestClient) -> None:
    """Der User traegt nichts ein - das Gewicht kommt aus dem Profil."""
    user_id = _create_user(client)  # weight 80.5
    plan_id = _create_plan(client, user_id)

    response = client.post(
        "/api/v1/workouts",
        json={"date": "2026-08-31T10:00:00Z", "workout_plan_id": plan_id},
    )
    assert response.status_code == 201
    assert response.json()["body_weight"] == 80.5


def test_geaendertes_profilgewicht_laesst_alte_einheiten_unberuehrt(
    client: TestClient,
) -> None:
    """Der springende Punkt der ganzen Spalte.

    Wuerde das Log appuser.weight nachschlagen, stuende nach dem PATCH auch
    neben der alten Einheit das neue Gewicht - das saehe aus wie Historie,
    waere aber keine.
    """
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    alt = client.post(
        "/api/v1/workouts",
        json={"date": "2026-03-01T10:00:00Z", "workout_plan_id": plan_id},
    ).json()

    client.patch(f"/api/v1/users/{user_id}", json={"weight": 78.0})

    neu = client.post(
        "/api/v1/workouts",
        json={"date": "2026-09-01T10:00:00Z", "workout_plan_id": plan_id},
    ).json()

    assert alt["body_weight"] == 80.5
    assert neu["body_weight"] == 78.0
    # Und die alte Einheit bleibt es auch beim erneuten Lesen.
    assert client.get(f"/api/v1/workouts/{alt['id']}").json()["body_weight"] == 80.5


def test_log_zeigt_das_gewicht_von_damals(client: TestClient) -> None:
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    client.post(
        "/api/v1/workouts",
        json={"date": "2026-03-01T10:00:00Z", "workout_plan_id": plan_id},
    )
    client.patch(f"/api/v1/users/{user_id}", json={"weight": 75.0})

    eintraege = client.get(f"/api/v1/users/{user_id}/log/workouts").json()
    assert eintraege[0]["body_weight"] == 80.5


# --- Offline-Synchronisation ---------------------------------------------


def _sync_payload(plan_id: int, day_id: int, exercise_id: int, uuid: str) -> dict:
    return {
        "client_uuid": uuid,
        "workout_plan_id": plan_id,
        "training_day_id": day_id,
        "date": "2026-08-31T17:00:00Z",
        "started_at": "2026-08-31T17:00:00Z",
        "finished_at": "2026-08-31T18:12:00Z",
        "comment": "im Keller ohne Empfang",
        "sets": [
            {"exercise_id": exercise_id, "repetitions": 8, "weight": 82.5},
            {"exercise_id": exercise_id, "repetitions": 7, "weight": 82.5},
        ],
    }


def test_sync_legt_einheit_mit_saetzen_in_einem_aufruf_an(client: TestClient) -> None:
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    exercise_id = _create_exercise(client, user_id, "Bankdruecken")
    day_id = _create_training_day(client, plan_id, 1, "Push")

    response = client.post(
        "/api/v1/workouts/sync",
        json=_sync_payload(plan_id, day_id, exercise_id, "aaaa-1111-bbbb-2222"),
    )
    assert response.status_code == 201, response.text
    daten = response.json()
    assert len(daten["sets"]) == 2
    assert daten["duration"] == "01:12:00"
    # Die Zeiten kommen aus der Nutzlast, nicht vom Server: sonst waere eine
    # am naechsten Morgen uebertragene Einheit Stunden zu lang.
    assert daten["started_at"].startswith("2026-08-31T17:00:00")
    assert daten["attended"] is True
    assert daten["body_weight"] == 80.5


def test_sync_haelt_die_plaetze_auseinander(client: TestClient) -> None:
    """Dieselbe Uebung zweimal am Tag: jeder Satz behaelt seinen Platz.

    Ohne training_day_exercise_id waeren "Bankdruecken 5x5" und
    "Bankdruecken 3x12" derselben Einheit hinterher nicht mehr zu trennen.
    """
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    exercise_id = _create_exercise(client, user_id, "Bankdruecken")
    day_id = _create_training_day(client, plan_id, 1, "Push")

    schwer = client.post(
        f"/api/v1/training-days/{day_id}/exercises",
        json={"exercise_id": exercise_id, "position": 1, "target_sets": 5},
    ).json()["id"]
    leicht = client.post(
        f"/api/v1/training-days/{day_id}/exercises",
        json={"exercise_id": exercise_id, "position": 2, "target_sets": 3},
    ).json()["id"]

    payload = _sync_payload(plan_id, day_id, exercise_id, "plaetze-1111-2222")
    payload["sets"] = [
        {"exercise_id": exercise_id, "repetitions": 5, "weight": 100.0,
         "training_day_exercise_id": schwer},
        {"exercise_id": exercise_id, "repetitions": 12, "weight": 60.0,
         "training_day_exercise_id": leicht},
    ]

    daten = client.post("/api/v1/workouts/sync", json=payload)
    assert daten.status_code == 201, daten.text
    saetze = daten.json()["sets"]
    assert [s["training_day_exercise_id"] for s in saetze] == [schwer, leicht]
    assert [s["repetitions"] for s in saetze] == [5, 12]


def test_sync_lehnt_platz_aus_fremdem_tag_ab(client: TestClient) -> None:
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    exercise_id = _create_exercise(client, user_id, "Bankdruecken")
    push = _create_training_day(client, plan_id, 1, "Push")
    pull = _create_training_day(client, plan_id, 2, "Pull")

    fremder_platz = client.post(
        f"/api/v1/training-days/{pull}/exercises", json={"exercise_id": exercise_id}
    ).json()["id"]

    payload = _sync_payload(plan_id, push, exercise_id, "fremder-platz-99")
    payload["sets"] = [
        {"exercise_id": exercise_id, "repetitions": 8,
         "training_day_exercise_id": fremder_platz}
    ]
    antwort = client.post("/api/v1/workouts/sync", json=payload)
    assert antwort.status_code == 422
    assert "gehoert nicht" in antwort.json()["detail"]


def test_sync_ohne_platz_bleibt_erlaubt(client: TestClient) -> None:
    """Freies Training und spontane Zusatzuebungen haben keinen Platz."""
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    exercise_id = _create_exercise(client, user_id, "Bankdruecken")
    day_id = _create_training_day(client, plan_id, 1, "Push")

    antwort = client.post(
        "/api/v1/workouts/sync",
        json=_sync_payload(plan_id, day_id, exercise_id, "ohne-platz-4321"),
    )
    assert antwort.status_code == 201
    assert all(s["training_day_exercise_id"] is None for s in antwort.json()["sets"])


def test_sync_ist_idempotent(client: TestClient) -> None:
    """Der Fall, um den es geht: Server schreibt, Antwort geht verloren.

    Das Handy wiederholt den Aufruf. Ohne client_uuid stuende die Einheit
    danach zweimal im Log.
    """
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    exercise_id = _create_exercise(client, user_id, "Bankdruecken")
    day_id = _create_training_day(client, plan_id, 1, "Push")
    payload = _sync_payload(plan_id, day_id, exercise_id, "gleiche-uuid-1234")

    erste = client.post("/api/v1/workouts/sync", json=payload)
    zweite = client.post("/api/v1/workouts/sync", json=payload)

    assert erste.status_code == 201
    # 200 statt 201: nichts Neues entstanden, aber auch kein Fehler - aus
    # Sicht des Handys ist genau das der Erfolgsfall.
    assert zweite.status_code == 200
    assert zweite.json()["id"] == erste.json()["id"]
    assert len(client.get(f"/api/v1/workouts?user_id={user_id}").json()) == 1
    assert len(zweite.json()["sets"]) == 2


def test_sync_ohne_trainingstag_ist_ein_freies_training(client: TestClient) -> None:
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    exercise_id = _create_exercise(client, user_id, "Liegestuetze", weighted=False)

    payload = _sync_payload(plan_id, 0, exercise_id, "custom-uuid-9999")
    payload["training_day_id"] = None
    payload["sets"] = [{"exercise_id": exercise_id, "repetitions": 20}]

    response = client.post("/api/v1/workouts/sync", json=payload)
    assert response.status_code == 201, response.text
    assert response.json()["is_custom"] is True


def test_sync_mit_fremder_uebung_wird_abgelehnt(client: TestClient) -> None:
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    day_id = _create_training_day(client, plan_id, 1, "Push")

    fremd = client.post(
        "/api/v1/users", json={"name": "Ben", "age": 25, "weight": 70.0}
    ).json()["id"]
    fremde_uebung = _create_exercise(client, fremd, "Bankdruecken")

    response = client.post(
        "/api/v1/workouts/sync",
        json=_sync_payload(plan_id, day_id, fremde_uebung, "fremd-uuid-0001"),
    )
    assert response.status_code == 422
    # Nichts darf halb angelegt worden sein.
    assert client.get(f"/api/v1/workouts?user_id={user_id}").json() == []


def test_sync_lehnt_gewicht_bei_koerpergewichtsuebung_ab(client: TestClient) -> None:
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    day_id = _create_training_day(client, plan_id, 1, "Pull")
    klimmzuege = _create_exercise(client, user_id, "Klimmzuege", weighted=False)

    payload = _sync_payload(plan_id, day_id, klimmzuege, "gewicht-uuid-0002")
    response = client.post("/api/v1/workouts/sync", json=payload)
    assert response.status_code == 422
    assert "nicht gewichtsbasiert" in response.json()["detail"]


def test_sync_lehnt_ende_vor_beginn_ab(client: TestClient) -> None:
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    day_id = _create_training_day(client, plan_id, 1, "Push")
    exercise_id = _create_exercise(client, user_id, "Bankdruecken")

    payload = _sync_payload(plan_id, day_id, exercise_id, "zeit-uuid-0003")
    payload["finished_at"] = "2026-08-31T16:00:00Z"
    assert client.post("/api/v1/workouts/sync", json=payload).status_code == 422


# --- Plan kopieren --------------------------------------------------------


def test_plan_duplizieren_kopiert_tage_und_vorgaben(client: TestClient) -> None:
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    bank = _create_exercise(client, user_id, "Bankdruecken")
    _create_training_day(
        client,
        plan_id,
        1,
        "Push",
        exercises=[
            {"exercise_id": bank, "position": 1, "target_sets": 3,
             "target_reps_min": 8, "target_reps_max": 10}
        ],
    )

    response = client.post(f"/api/v1/workout-plans/{plan_id}/duplicate", json={})
    assert response.status_code == 201, response.text
    kopie = response.json()

    assert kopie["id"] != plan_id
    assert kopie["title"] == "Push/Pull (Copy)"
    assert kopie["training_days_per_week"] == 1
    tag = kopie["training_days"][0]
    assert tag["workout_type"] == "Push"
    vorgabe = tag["exercise_links"][0]
    assert vorgabe["target_sets"] == 3
    assert vorgabe["target_reps_min"] == 8
    assert vorgabe["target_reps_max"] == 10


def test_kopie_verweist_auf_dieselbe_katalog_uebung(client: TestClient) -> None:
    """Der Grund, warum die Kopie nur Verweise kopiert.

    Wuerde sie die Uebungen mitkopieren, haetten beide Plaene eine eigene
    Zeile "Bankdruecken" - und der Monatsvergleich ueber den Planwechsel
    hinweg faende nichts mehr. Genau das hat Phase 1 abgeschafft.
    """
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    bank = _create_exercise(client, user_id, "Bankdruecken")
    _create_training_day(
        client, plan_id, 1, "Push", exercises=[{"exercise_id": bank}]
    )

    kopie = client.post(f"/api/v1/workout-plans/{plan_id}/duplicate", json={}).json()

    assert kopie["training_days"][0]["exercise_links"][0]["exercise_id"] == bank
    # Und der Katalog ist dadurch nicht gewachsen.
    katalog = client.get(f"/api/v1/exercises?user_id={user_id}").json()
    assert len(katalog) == 1


def test_kopie_uebernimmt_keine_einheiten(client: TestClient) -> None:
    """Die Historie gehoert zum alten Plan - der neue hat noch keine."""
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    client.post(
        "/api/v1/workouts",
        json={"date": "2026-08-01T10:00:00Z", "workout_plan_id": plan_id},
    )

    kopie = client.post(f"/api/v1/workout-plans/{plan_id}/duplicate", json={}).json()

    assert client.get(f"/api/v1/workouts?workout_plan_id={kopie['id']}").json() == []
    assert len(client.get(f"/api/v1/workouts?workout_plan_id={plan_id}").json()) == 1


def test_kopie_uebernimmt_die_zeitraeume_nicht(client: TestClient) -> None:
    user_id = _create_user(client)
    plan_id = client.post(
        "/api/v1/workout-plans",
        json={
            "title": "Herbst",
            "user_id": user_id,
            "starting_date": "2025-09-01",
            "ending_date": "2025-12-31",
        },
    ).json()["id"]

    kopie = client.post(f"/api/v1/workout-plans/{plan_id}/duplicate", json={}).json()
    assert kopie["starting_date"] is None
    assert kopie["ending_date"] is None


def test_kopie_nimmt_einen_eigenen_titel_an(client: TestClient) -> None:
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    kopie = client.post(
        f"/api/v1/workout-plans/{plan_id}/duplicate", json={"title": "Fruehjahr 2027"}
    ).json()
    assert kopie["title"] == "Fruehjahr 2027"


def test_duplizieren_eines_unbekannten_plans_gibt_404(client: TestClient) -> None:
    assert client.post("/api/v1/workout-plans/999/duplicate", json={}).status_code == 404
