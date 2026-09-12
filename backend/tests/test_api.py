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
        "/api/v1/workout-plans", json={"title": "Push/Pull", "user_id": user_id}
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_exercise(
    client: TestClient, user_id: int, title: str, *, weighted: bool = True
) -> int:
    """Uebungen haengen am User, nicht am Plan - deshalb reicht die user_id."""
    response = client.post(
        "/api/v1/exercises",
        json={"title": title, "weighted": weighted, "user_id": user_id},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_training_day(
    client: TestClient, plan_id: int, position: int, workout_type: str, exercises=None
) -> int:
    response = client.post(
        "/api/v1/training-days",
        json={
            "workout_plan_id": plan_id,
            "position": position,
            "workout_type": workout_type,
            "exercises": exercises or [],
        },
    )
    assert response.status_code == 201, response.text
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
        json={"title": "Plan", "user_id": 9999},
    )
    assert response.status_code == 404


def test_plan_detail_enthaelt_trainingstage_mit_vorgaben(client: TestClient) -> None:
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    exercise_id = _create_exercise(client, user_id, "Bankdruecken")
    _create_training_day(
        client,
        plan_id,
        1,
        "Push",
        [{"exercise_id": exercise_id, "target_sets": 3}],
    )

    plan = client.get(f"/api/v1/workout-plans/{plan_id}").json()
    assert plan["training_days_per_week"] == 1
    tag = plan["training_days"][0]
    assert tag["workout_type"] == "Push"
    vorgabe = tag["exercise_links"][0]
    assert vorgabe["exercise"]["title"] == "Bankdruecken"
    assert vorgabe["target_sets"] == 3
    # Der Plan gibt nur Saetze vor - Wiederholungen kennt er nicht.
    assert "target_reps_min" not in vorgabe


def test_workout_detail_enthaelt_protokollierte_saetze(client: TestClient) -> None:
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    exercise_id = _create_exercise(
        client, user_id, "Kniebeuge", weighted=True
    )

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
    exercise_id = _create_exercise(
        client, user_id, "Kniebeuge", weighted=True
    )

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


def test_satz_mit_fremder_uebung_wird_abgelehnt(client: TestClient) -> None:
    """Uebungen gehoeren dem User - Annas Bankdruecken in Bens Einheit waere Unsinn."""
    anna = _create_user(client)
    ben = client.post(
        "/api/v1/users", json={"name": "Ben", "age": 34, "weight": 82.0}
    ).json()["id"]
    annas_uebung = _create_exercise(client, anna, "Bankdruecken")
    bens_workout = _create_workout(client, _create_plan(client, ben))

    response = client.post(
        "/api/v1/sets",
        json={
            "repetitions": 8,
            "weight": 60,
            "exercise_id": annas_uebung,
            "workout_id": bens_workout,
        },
    )
    assert response.status_code == 422


def test_dieselbe_uebung_in_zwei_plaenen(client: TestClient) -> None:
    """Der Kern des Katalogs: eine Uebung ueberlebt den Planwechsel.

    Waere die Uebung an den Plan gebunden, haette sie hier zwei ids - und der
    Monatsvergleich ueber den Planwechsel hinweg faende nichts zu vergleichen.
    """
    user_id = _create_user(client)
    alter_plan = _create_plan(client, user_id)
    neuer_plan = _create_plan(client, user_id)
    bank = _create_exercise(client, user_id, "Bankdruecken")

    for plan_id in (alter_plan, neuer_plan):
        workout_id = _create_workout(client, plan_id)
        antwort = client.post(
            "/api/v1/sets",
            json={
                "repetitions": 8,
                "weight": 60,
                "exercise_id": bank,
                "workout_id": workout_id,
            },
        )
        assert antwort.status_code == 201

    saetze = client.get(f"/api/v1/sets?exercise_id={bank}").json()
    assert len(saetze) == 2


def test_satz_mit_gewicht_bei_koerpergewichtsuebung_abgelehnt(
    client: TestClient,
) -> None:
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    exercise_id = _create_exercise(
        client, user_id, "Klimmzuege", weighted=False
    )

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


# --- Aktiver Plan ----------------------------------------------------------


def test_genau_ein_aktiver_plan(client: TestClient) -> None:
    """Die Auswahl ersetzt sich selbst - zwei aktive Plaene sind unmoeglich."""
    user_id = _create_user(client)
    sommer = _create_plan(client, user_id)
    herbst = _create_plan(client, user_id)

    assert client.get(f"/api/v1/users/{user_id}").json()["active_workout_plan_id"] is None
    # Ohne Auswahl gibt es keinen aktiven Plan zu laden.
    assert client.get(f"/api/v1/users/{user_id}/active-plan").status_code == 404

    client.put(f"/api/v1/users/{user_id}/active-plan", json={"workout_plan_id": sommer})
    assert client.get(f"/api/v1/users/{user_id}").json()["active_workout_plan_id"] == sommer

    client.put(f"/api/v1/users/{user_id}/active-plan", json={"workout_plan_id": herbst})
    assert client.get(f"/api/v1/users/{user_id}").json()["active_workout_plan_id"] == herbst
    assert client.get(f"/api/v1/users/{user_id}/active-plan").json()["id"] == herbst

    # null hebt die Auswahl wieder auf
    client.put(f"/api/v1/users/{user_id}/active-plan", json={"workout_plan_id": None})
    assert client.get(f"/api/v1/users/{user_id}").json()["active_workout_plan_id"] is None


def test_fremder_plan_kann_nicht_aktiv_gesetzt_werden(client: TestClient) -> None:
    anna = _create_user(client)
    ben = client.post(
        "/api/v1/users", json={"name": "Ben", "age": 34, "weight": 82.0}
    ).json()["id"]
    bens_plan = _create_plan(client, ben)

    response = client.put(
        f"/api/v1/users/{anna}/active-plan", json={"workout_plan_id": bens_plan}
    )
    assert response.status_code == 422


# --- Trainingstage ---------------------------------------------------------


def test_plan_mit_trainingstagen_in_einem_request(client: TestClient) -> None:
    user_id = _create_user(client)
    bank = _create_exercise(client, user_id, "Bankdruecken")
    kniebeuge = _create_exercise(client, user_id, "Kniebeuge")

    plan_id = client.post(
        "/api/v1/workout-plans",
        json={
            "title": "Push/Pull/Legs",
            "user_id": user_id,
            "training_days": [
                {
                    "position": 1,
                    "workout_type": "Push",
                    "exercises": [{"exercise_id": bank, "target_sets": 3}],
                },
                {
                    "position": 2,
                    "workout_type": "Legs",
                    "exercises": [{"exercise_id": kniebeuge, "target_sets": 4}],
                },
            ],
        },
    ).json()["id"]

    plan = client.get(f"/api/v1/workout-plans/{plan_id}").json()
    assert plan["training_days_per_week"] == 2
    assert [tag["workout_type"] for tag in plan["training_days"]] == ["Push", "Legs"]


def test_position_ist_je_plan_einmalig(client: TestClient) -> None:
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    _create_training_day(client, plan_id, 1, "Push")

    doppelt = client.post(
        "/api/v1/training-days",
        json={"workout_plan_id": plan_id, "position": 1, "workout_type": "Pull"},
    )
    assert doppelt.status_code == 409


def test_gleicher_typ_zweimal_ist_erlaubt(client: TestClient) -> None:
    """Ein 4er-Split darf zweimal "Push" enthalten - mit anderen Uebungen."""
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    _create_training_day(client, plan_id, 1, "Push")
    zweiter = client.post(
        "/api/v1/training-days",
        json={"workout_plan_id": plan_id, "position": 2, "workout_type": "Push"},
    )
    assert zweiter.status_code == 201


def test_vorgabe_laesst_sich_aendern(client: TestClient) -> None:
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    bank = _create_exercise(client, user_id, "Bankdruecken")
    tag = _create_training_day(client, plan_id, 1, "Push")

    platz = client.post(
        f"/api/v1/training-days/{tag}/exercises",
        json={"exercise_id": bank, "target_sets": 3},
    ).json()["id"]
    geaendert = client.patch(
        f"/api/v1/training-days/{tag}/exercises/{platz}",
        json={"target_sets": 4},
    )
    assert geaendert.status_code == 200
    assert geaendert.json()["target_sets"] == 4
    # Und die Aenderung steht auch beim erneuten Lesen im Plan - der
    # Save-Knopf im Editor haette sonst nichts, worauf er sich verlassen kann.
    tag_gelesen = client.get(f"/api/v1/training-days/{tag}").json()
    assert tag_gelesen["exercise_links"][0]["target_sets"] == 4

    # 0 Saetze ist keine Vorgabe, sondern ein Tippfehler.
    kaputt = client.patch(
        f"/api/v1/training-days/{tag}/exercises/{platz}",
        json={"target_sets": 0},
    )
    assert kaputt.status_code == 422


def test_uebung_darf_pro_tag_mehrfach_stehen(client: TestClient) -> None:
    """Bankdruecken schwer am Anfang, leicht am Ende - zwei eigene Plaetze."""
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    bank = _create_exercise(client, user_id, "Bankdruecken")
    tag = _create_training_day(client, plan_id, 1, "Push")

    schwer = client.post(
        f"/api/v1/training-days/{tag}/exercises",
        json={"exercise_id": bank, "position": 1, "target_sets": 5},
    )
    leicht = client.post(
        f"/api/v1/training-days/{tag}/exercises",
        json={"exercise_id": bank, "position": 2, "target_sets": 3},
    )
    assert schwer.status_code == 201
    assert leicht.status_code == 201
    # Zwei Plaetze, dieselbe Uebung, eigene ids und eigene Vorgaben.
    assert schwer.json()["id"] != leicht.json()["id"]
    assert schwer.json()["exercise_id"] == leicht.json()["exercise_id"] == bank

    tag_gelesen = client.get(f"/api/v1/training-days/{tag}").json()
    assert len(tag_gelesen["exercise_links"]) == 2
    assert [link["target_sets"] for link in tag_gelesen["exercise_links"]] == [5, 3]


def test_platz_laesst_sich_einzeln_entfernen(client: TestClient) -> None:
    """Einen der beiden Plaetze streichen laesst den anderen unberuehrt."""
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    bank = _create_exercise(client, user_id, "Bankdruecken")
    tag = _create_training_day(client, plan_id, 1, "Push")

    erster = client.post(
        f"/api/v1/training-days/{tag}/exercises", json={"exercise_id": bank}
    ).json()["id"]
    zweiter = client.post(
        f"/api/v1/training-days/{tag}/exercises", json={"exercise_id": bank}
    ).json()["id"]

    assert (
        client.delete(f"/api/v1/training-days/{tag}/exercises/{erster}").status_code
        == 204
    )
    uebrig = client.get(f"/api/v1/training-days/{tag}").json()["exercise_links"]
    assert [link["id"] for link in uebrig] == [zweiter]


def test_fremder_platz_wird_abgelehnt(client: TestClient) -> None:
    """Die id eines Platzes aus einem anderen Tag darf nichts aendern."""
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    bank = _create_exercise(client, user_id, "Bankdruecken")
    push = _create_training_day(client, plan_id, 1, "Push")
    pull = _create_training_day(client, plan_id, 2, "Pull")

    platz = client.post(
        f"/api/v1/training-days/{push}/exercises", json={"exercise_id": bank}
    ).json()["id"]

    assert (
        client.patch(
            f"/api/v1/training-days/{pull}/exercises/{platz}", json={"target_sets": 4}
        ).status_code
        == 404
    )
    assert (
        client.delete(f"/api/v1/training-days/{pull}/exercises/{platz}").status_code
        == 404
    )


# --- Custom-Workouts -------------------------------------------------------


def test_workout_ohne_trainingstag_ist_custom(client: TestClient) -> None:
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    tag = _create_training_day(client, plan_id, 1, "Push")

    geplant = client.post(
        "/api/v1/workouts",
        json={
            "date": "2026-08-31T10:00:00Z",
            "workout_plan_id": plan_id,
            "training_day_id": tag,
        },
    ).json()
    assert geplant["is_custom"] is False

    frei = client.post(
        "/api/v1/workouts",
        json={"date": "2026-08-31T10:00:00Z", "workout_plan_id": plan_id},
    ).json()
    assert frei["is_custom"] is True
    assert frei["training_day_id"] is None


def test_trainingstag_aus_fremdem_plan_wird_abgelehnt(client: TestClient) -> None:
    user_id = _create_user(client)
    plan_a = _create_plan(client, user_id)
    plan_b = _create_plan(client, user_id)
    tag_a = _create_training_day(client, plan_a, 1, "Push")

    response = client.post(
        "/api/v1/workouts",
        json={
            "date": "2026-08-31T10:00:00Z",
            "workout_plan_id": plan_b,
            "training_day_id": tag_a,
        },
    )
    assert response.status_code == 422


# --- Uebungskatalog --------------------------------------------------------


def test_doppelter_uebungsname_wird_abgelehnt(client: TestClient) -> None:
    """Zwei "Bankdruecken" wuerden den Verlauf in zwei Haelften zerlegen."""
    user_id = _create_user(client)
    _create_exercise(client, user_id, "Bankdruecken")

    doppelt = client.post(
        "/api/v1/exercises",
        json={"title": "Bankdruecken", "weighted": True, "user_id": user_id},
    )
    assert doppelt.status_code == 409

    # auch mit anderer Schreibweise
    anders = client.post(
        "/api/v1/exercises",
        json={"title": "bankdruecken", "weighted": True, "user_id": user_id},
    )
    assert anders.status_code == 409

    # ein anderer User darf denselben Namen haben
    ben = client.post(
        "/api/v1/users", json={"name": "Ben", "age": 34, "weight": 82.0}
    ).json()["id"]
    assert (
        client.post(
            "/api/v1/exercises",
            json={"title": "Bankdruecken", "weighted": True, "user_id": ben},
        ).status_code
        == 201
    )


def test_katalog_filterbar_nach_user_und_plan(client: TestClient) -> None:
    user_id = _create_user(client)
    bank = _create_exercise(client, user_id, "Bankdruecken")
    _create_exercise(client, user_id, "Kniebeuge")
    plan_id = _create_plan(client, user_id)
    _create_training_day(client, plan_id, 1, "Push", [{"exercise_id": bank}])

    assert len(client.get(f"/api/v1/exercises?user_id={user_id}").json()) == 2
    # Der Plan kennt nur die Uebung, die auch auf einem seiner Tage steht.
    im_plan = client.get(f"/api/v1/exercises?workout_plan_id={plan_id}").json()
    assert [u["title"] for u in im_plan] == ["Bankdruecken"]


def test_einheit_loeschen_raeumt_das_log_auf(client: TestClient) -> None:
    """Der Knopf "Session loeschen" in der Detailansicht.

    Geprueft wird nicht nur der Statuscode, sondern dass die Einheit danach
    auch aus dem Log verschwunden ist - ein Eintrag, der nur nicht mehr
    abrufbar ist, aber weiter in der Liste steht, waere der schlimmere Fehler.
    """
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    bank = _create_exercise(client, user_id, "Bankdruecken")
    tag = _create_training_day(client, plan_id, 1, "Push")
    einheit = client.post(
        "/api/v1/workouts",
        json={
            "date": "2026-09-01T10:00:00Z",
            "workout_plan_id": plan_id,
            "training_day_id": tag,
        },
    ).json()["id"]
    client.post(
        "/api/v1/sets",
        json={
            "exercise_id": bank,
            "workout_id": einheit,
            "repetitions": 8,
            "weight": 82.5,
        },
    )
    assert len(client.get(f"/api/v1/users/{user_id}/log/workouts").json()) == 1

    assert client.delete(f"/api/v1/workouts/{einheit}").status_code == 204

    assert client.get(f"/api/v1/workouts/{einheit}").status_code == 404
    assert client.get(f"/api/v1/users/{user_id}/log/workouts").json() == []
    # Die Saetze gehen mit (ondelete=CASCADE), der Katalogeintrag bleibt.
    assert client.get("/api/v1/sets", params={"workout_id": einheit}).json() == []
    assert client.get(f"/api/v1/exercises/{bank}").status_code == 200


def test_luecke_in_den_positionen_laesst_sich_wieder_fuellen(client: TestClient) -> None:
    """Der Vertrag, auf den sich "Add training day" im Editor stuetzt.

    Der Editor hat die Position lange aus der ANZAHL der Tage abgeleitet
    (length + 1). Nach dem Loeschen des mittleren von drei Tagen bleiben die
    Positionen 1 und 3 stehen - length + 1 ist dann 3 und damit belegt, der
    Aufruf lief in eine 409, und im Editor passierte sichtbar nichts. Zaehlen
    ist kein Numerieren, sobald in der Mitte etwas wegfallen kann.

    Geprueft wird beides: dass die belegte Position abgelehnt wird, und dass
    die freie Position 2 die Luecke wirklich schliesst.
    """
    user_id = _create_user(client)
    plan_id = _create_plan(client, user_id)
    for position in (1, 2, 3):
        _create_training_day(client, plan_id, position, f"Tag {position}")

    tage = client.get(f"/api/v1/workout-plans/{plan_id}").json()["training_days"]
    mitte = next(tag["id"] for tag in tage if tag["position"] == 2)
    assert client.delete(f"/api/v1/training-days/{mitte}").status_code == 204

    belegt = client.post(
        "/api/v1/training-days",
        json={"workout_plan_id": plan_id, "position": 3, "workout_type": "Beine"},
    )
    assert belegt.status_code == 409

    frei = client.post(
        "/api/v1/training-days",
        json={"workout_plan_id": plan_id, "position": 2, "workout_type": "Beine"},
    )
    assert frei.status_code == 201, frei.text

    # Und der Plan liefert die Tage nach Position sortiert aus - der Editor
    # zeigt sie in genau dieser Reihenfolge an.
    plan = client.get(f"/api/v1/workout-plans/{plan_id}").json()
    assert [tag["position"] for tag in plan["training_days"]] == [1, 2, 3]
    assert [tag["workout_type"] for tag in plan["training_days"]] == ["Tag 1", "Beine", "Tag 3"]
    assert plan["training_days_per_week"] == 3
