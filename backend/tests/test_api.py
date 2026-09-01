"""Tests der Endpunkte ueber HTTP (TestClient)."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient


def _create_user(client: TestClient) -> int:
    response = client.post(
        "/api/v1/users", json={"name": "Daniel", "age": 30, "weight": 80.5}
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_plan(client: TestClient, user_id: int) -> int:
    response = client.post(
        "/api/v1/workout-plans",
        json={"title": "Push/Pull", "training_days": 4, "user_id": user_id},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_workout(client: TestClient, plan_id: int) -> int:
    response = client.post(
        "/api/v1/workouts",
        json={"date": "2026-08-31T10:00:00Z", "workout_plan_id": plan_id},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_user_crud(client: TestClient) -> None:
    user_id = _create_user(client)

    assert client.get(f"/api/v1/users/{user_id}").json()["name"] == "Daniel"
    assert len(client.get("/api/v1/users").json()) == 1

    updated = client.patch(f"/api/v1/users/{user_id}", json={"weight": 82.0}).json()
    assert updated["weight"] == 82.0
    assert updated["name"] == "Daniel"  # nicht gesendete Felder bleiben stehen

    assert client.delete(f"/api/v1/users/{user_id}").status_code == 204
    assert client.get(f"/api/v1/users/{user_id}").status_code == 404


def test_unbekannte_id_gibt_404_mit_lesbarer_meldung(client: TestClient) -> None:
    response = client.get("/api/v1/users/9999")
    assert response.status_code == 404
    # die id muss in der Meldung stehen (frueher stand dort woertlich "{item_id}")
    assert "9999" in response.json()["detail"]


def test_ungueltige_eingabe_gibt_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/users", json={"name": "X", "age": -5, "weight": 80}
    )
    assert response.status_code == 422


def test_plan_fuer_unbekannten_user_gibt_404_statt_500(client: TestClient) -> None:
    response = client.post(
        "/api/v1/workout-plans",
        json={"title": "Plan", "training_days": 3, "user_id": 9999},
    )
    assert response.status_code == 404


def test_plan_detail_enthaelt_uebungen_und_saetze(client: TestClient) -> None:
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    workout_id = _create_workout(client, plan_id)
    exercise_id = client.post(
        "/api/v1/exercises",
        json={"title": "Bankdruecken", "weighted": True, "workout_plan_id": plan_id},
    ).json()["id"]
    client.post(
        "/api/v1/sets",
        json={
            "repetitions": 8,
            "weight": 60,
            "exercise_id": exercise_id,
            "workout_id": workout_id,
        },
    )

    plan = client.get(f"/api/v1/workout-plans/{plan_id}").json()
    assert plan["exercises"][0]["title"] == "Bankdruecken"
    assert plan["exercises"][0]["sets"][0]["repetitions"] == 8


def test_workout_detail_enthaelt_protokollierte_saetze(client: TestClient) -> None:
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    exercise_id = client.post(
        "/api/v1/exercises",
        json={"title": "Kniebeuge", "weighted": True, "workout_plan_id": plan_id},
    ).json()["id"]

    montag = _create_workout(client, plan_id)
    for gewicht in (60, 65):
        client.post(
            "/api/v1/sets",
            json={
                "repetitions": 8,
                "weight": gewicht,
                "exercise_id": exercise_id,
                "workout_id": montag,
            },
        )

    detail = client.get(f"/api/v1/workouts/{montag}").json()
    assert len(detail["sets"]) == 2
    assert detail["sets"][0]["workout_id"] == montag

    gefiltert = client.get(f"/api/v1/sets?workout_id={montag}").json()
    assert len(gefiltert) == 2


def test_satz_ohne_workout_wird_abgelehnt(client: TestClient) -> None:
    """Ein Satz braucht zwingend eine Einheit - das ist der Kern des Modells."""
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    exercise_id = client.post(
        "/api/v1/exercises",
        json={"title": "Kniebeuge", "weighted": True, "workout_plan_id": plan_id},
    ).json()["id"]

    ohne = client.post(
        "/api/v1/sets", json={"repetitions": 8, "weight": 60, "exercise_id": exercise_id}
    )
    assert ohne.status_code == 422

    unbekannt = client.post(
        "/api/v1/sets",
        json={
            "repetitions": 8,
            "weight": 60,
            "exercise_id": exercise_id,
            "workout_id": 9999,
        },
    )
    assert unbekannt.status_code == 404


def test_satz_aus_fremdem_plan_wird_abgelehnt(client: TestClient) -> None:
    user_id = _create_user(client)
    plan_a = _create_plan(client, user_id)
    plan_b = _create_plan(client, user_id)
    exercise_a = client.post(
        "/api/v1/exercises",
        json={"title": "Bankdruecken", "weighted": True, "workout_plan_id": plan_a},
    ).json()["id"]
    workout_b = _create_workout(client, plan_b)

    response = client.post(
        "/api/v1/sets",
        json={
            "repetitions": 8,
            "weight": 60,
            "exercise_id": exercise_a,
            "workout_id": workout_b,
        },
    )
    assert response.status_code == 422


def test_satz_mit_gewicht_bei_koerpergewichtsuebung_abgelehnt(
    client: TestClient,
) -> None:
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    exercise_id = client.post(
        "/api/v1/exercises",
        json={"title": "Klimmzuege", "weighted": False, "workout_plan_id": plan_id},
    ).json()["id"]

    workout_id = _create_workout(client, plan_id)

    abgelehnt = client.post(
        "/api/v1/sets",
        json={
            "repetitions": 10,
            "weight": 20,
            "exercise_id": exercise_id,
            "workout_id": workout_id,
        },
    )
    assert abgelehnt.status_code == 422

    ok = client.post(
        "/api/v1/sets",
        json={"repetitions": 10, "exercise_id": exercise_id, "workout_id": workout_id},
    )
    assert ok.status_code == 201
    assert ok.json()["weight"] is None


def test_workouts_filterbar_nach_user(client: TestClient) -> None:
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    client.post(
        "/api/v1/workouts",
        json={
            "date": "2026-08-31T10:00:00Z",
            "attended": True,
            "comment": "gut gelaufen",
            "workout_plan_id": plan_id,
        },
    )

    assert len(client.get(f"/api/v1/workouts?user_id={user_id}").json()) == 1
    assert client.get("/api/v1/workouts?user_id=9999").json() == []


def test_workout_start_und_finish_ergibt_dauer(client: TestClient) -> None:
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    workout_id = _create_workout(client, plan_id)

    neu = client.get(f"/api/v1/workouts/{workout_id}").json()
    assert neu["started_at"] is None
    assert neu["duration_seconds"] is None
    assert neu["is_running"] is False

    gestartet = client.post(f"/api/v1/workouts/{workout_id}/start").json()
    assert gestartet["started_at"] is not None
    assert gestartet["finished_at"] is None
    assert gestartet["is_running"] is True
    assert gestartet["duration_seconds"] is None  # laeuft noch

    beendet = client.post(f"/api/v1/workouts/{workout_id}/finish").json()
    assert beendet["finished_at"] is not None
    assert beendet["is_running"] is False
    assert beendet["duration_seconds"] >= 0


def test_workout_kann_nicht_zweimal_gestartet_werden(client: TestClient) -> None:
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    workout_id = _create_workout(client, plan_id)

    assert client.post(f"/api/v1/workouts/{workout_id}/start").status_code == 200
    nochmal = client.post(f"/api/v1/workouts/{workout_id}/start")
    assert nochmal.status_code == 409

    client.post(f"/api/v1/workouts/{workout_id}/finish")
    assert client.post(f"/api/v1/workouts/{workout_id}/finish").status_code == 409


def test_finish_ohne_start_wird_abgelehnt(client: TestClient) -> None:
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    workout_id = _create_workout(client, plan_id)

    assert client.post(f"/api/v1/workouts/{workout_id}/finish").status_code == 409


def test_nachgetragene_zeiten_werden_geprueft(client: TestClient) -> None:
    """Vergangene Einheit nachtragen: erlaubt, aber nicht mit Unsinn-Zeitraum."""
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)

    verdreht = client.post(
        "/api/v1/workouts",
        json={
            "date": "2026-08-31T10:00:00Z",
            "workout_plan_id": plan_id,
            "started_at": "2026-08-31T11:00:00Z",
            "finished_at": "2026-08-31T10:00:00Z",
        },
    )
    assert verdreht.status_code == 422

    ohne_start = client.post(
        "/api/v1/workouts",
        json={
            "date": "2026-08-31T10:00:00Z",
            "workout_plan_id": plan_id,
            "finished_at": "2026-08-31T11:00:00Z",
        },
    )
    assert ohne_start.status_code == 422

    ok = client.post(
        "/api/v1/workouts",
        json={
            "date": "2026-08-31T10:00:00Z",
            "workout_plan_id": plan_id,
            "started_at": "2026-08-31T10:00:00Z",
            "finished_at": "2026-08-31T11:30:00Z",
        },
    )
    assert ok.status_code == 201
    assert ok.json()["duration_seconds"] == 5400


def test_patch_prueft_zeiten_gegen_bestehenden_stand(client: TestClient) -> None:
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    workout_id = _create_workout(client, plan_id)

    # finished_at allein, ohne dass je gestartet wurde
    nur_ende = client.patch(
        f"/api/v1/workouts/{workout_id}",
        json={"finished_at": "2026-08-31T11:00:00Z"},
    )
    assert nur_ende.status_code == 422

    client.patch(
        f"/api/v1/workouts/{workout_id}",
        json={"started_at": "2026-08-31T10:00:00Z"},
    )
    # jetzt ein Ende vor dem gespeicherten Start
    zu_frueh = client.patch(
        f"/api/v1/workouts/{workout_id}",
        json={"finished_at": "2026-08-31T09:00:00Z"},
    )
    assert zu_frueh.status_code == 422


def test_dauer_wird_formatiert_ausgegeben(client: TestClient) -> None:
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)

    workout = client.post(
        "/api/v1/workouts",
        json={
            "date": "2026-08-31T10:00:00Z",
            "workout_plan_id": plan_id,
            "started_at": "2026-08-31T10:00:00Z",
            "finished_at": "2026-08-31T11:43:32Z",
        },
    ).json()
    assert workout["duration"] == "01:43:32"
    assert workout["duration_seconds"] == 6212

    # Laufende Einheit hat noch keine Dauer
    offen = client.post(
        "/api/v1/workouts",
        json={"date": "2026-08-31T10:00:00Z", "workout_plan_id": plan_id},
    ).json()
    assert offen["duration"] is None


def test_vergessene_einheit_wird_nach_sechs_stunden_geschlossen(
    client: TestClient,
) -> None:
    """Wer /finish vergisst, soll keine ewig laufende Einheit hinterlassen."""
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)

    # Start vor 9 Stunden, nie beendet - via PATCH nachgestellt
    vergessen = _create_workout(client, plan_id)
    lange_her = (datetime.now(timezone.utc) - timedelta(hours=9)).isoformat()
    client.patch(f"/api/v1/workouts/{vergessen}", json={"started_at": lange_her})

    # Erst der naechste Lesezugriff raeumt auf
    geschlossen = client.get(f"/api/v1/workouts/{vergessen}").json()
    assert geschlossen["is_running"] is False
    assert geschlossen["duration"] == "06:00:00"

    # Und ein /finish geht danach nicht mehr - die Einheit ist zu
    assert client.post(f"/api/v1/workouts/{vergessen}/finish").status_code == 409


def test_frische_einheit_wird_nicht_geschlossen(client: TestClient) -> None:
    """Die Aufraeumaktion darf laufende Einheiten nicht abwuergen."""
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    workout_id = _create_workout(client, plan_id)
    client.post(f"/api/v1/workouts/{workout_id}/start")

    laeuft = client.get(f"/api/v1/workouts/{workout_id}").json()
    assert laeuft["is_running"] is True
    assert laeuft["finished_at"] is None
