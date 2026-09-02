"""Tests des Trainingslogs - Historie und Monatsvergleich.

Die Daten werden hier absichtlich mit festen Datumsangaben gebaut statt
relativ zu "heute": eine Auswertung, die je nach Testtag andere Monate
vergleicht, waere nicht reproduzierbar.
"""

from fastapi.testclient import TestClient

BASIS = "/api/v1"


def _setup(client: TestClient) -> dict:
    """Ein User mit Plan, zwei Trainingstagen und Uebungskatalog."""
    user_id = client.post(
        f"{BASIS}/users", json={"name": "Daniel", "age": 30, "weight": 80.5}
    ).json()["id"]

    bank = client.post(
        f"{BASIS}/exercises",
        json={"title": "Bankdruecken", "weighted": True, "user_id": user_id},
    ).json()["id"]
    klimmzug = client.post(
        f"{BASIS}/exercises",
        json={"title": "Klimmzuege", "weighted": False, "user_id": user_id},
    ).json()["id"]

    plan_id = client.post(
        f"{BASIS}/workout-plans", json={"title": "Push/Pull", "user_id": user_id}
    ).json()["id"]
    tag_id = client.post(
        f"{BASIS}/training-days",
        json={"workout_plan_id": plan_id, "position": 1, "workout_type": "Push"},
    ).json()["id"]

    return {
        "user_id": user_id,
        "plan_id": plan_id,
        "tag_id": tag_id,
        "bank": bank,
        "klimmzug": klimmzug,
    }


def _workout(client: TestClient, ctx: dict, datum: str, *, custom: bool = False) -> int:
    body = {"date": datum, "workout_plan_id": ctx["plan_id"]}
    if not custom:
        body["training_day_id"] = ctx["tag_id"]
    return client.post(f"{BASIS}/workouts", json=body).json()["id"]


def _satz(client: TestClient, workout_id: int, exercise_id: int, reps: int, weight=None):
    body = {"repetitions": reps, "exercise_id": exercise_id, "workout_id": workout_id}
    if weight is not None:
        body["weight"] = weight
    antwort = client.post(f"{BASIS}/sets", json=body)
    assert antwort.status_code == 201, antwort.text
    return antwort


def test_historie_zeigt_typ_und_custom(client: TestClient) -> None:
    ctx = _setup(client)
    geplant = _workout(client, ctx, "2026-04-06T18:00:00Z")
    _satz(client, geplant, ctx["bank"], 8, 80)
    frei = _workout(client, ctx, "2026-04-20T18:00:00Z", custom=True)
    _satz(client, frei, ctx["klimmzug"], 10)

    log = client.get(f"{BASIS}/users/{ctx['user_id']}/log/workouts").json()
    assert len(log) == 2
    # neueste zuerst
    assert log[0]["workout_type"] == "Custom"
    assert log[0]["is_custom"] is True
    assert log[1]["workout_type"] == "Push"
    assert log[1]["is_custom"] is False
    assert log[1]["plan_title"] == "Push/Pull"
    assert log[1]["set_count"] == 1


def test_monatsliste_nur_mit_einheiten(client: TestClient) -> None:
    ctx = _setup(client)
    _workout(client, ctx, "2025-09-10T18:00:00Z")
    _workout(client, ctx, "2026-04-10T18:00:00Z")
    _workout(client, ctx, "2026-04-24T18:00:00Z")

    monate = client.get(f"{BASIS}/users/{ctx['user_id']}/log/months").json()
    assert [m["month"] for m in monate] == ["2026-04", "2025-09"]
    assert [m["label"] for m in monate] == ["04/2026", "09/2025"]
    assert monate[0]["workout_count"] == 2


def test_fortschritt_zwischen_zwei_monaten(client: TestClient) -> None:
    """Der Fall aus der Spezifikation: 09/25 gegen 04/26."""
    ctx = _setup(client)

    september = _workout(client, ctx, "2025-09-10T18:00:00Z")
    _satz(client, september, ctx["bank"], 10, 70)
    _satz(client, september, ctx["bank"], 8, 75)

    april = _workout(client, ctx, "2026-04-10T18:00:00Z")
    _satz(client, april, ctx["bank"], 8, 85)
    _satz(client, april, ctx["bank"], 6, 90)

    antwort = client.get(
        f"{BASIS}/users/{ctx['user_id']}/log/progress",
        params={"month_a": "2025-09", "month_b": "2026-04"},
    ).json()

    assert antwort["label_a"] == "09/2025"
    assert antwort["label_b"] == "04/2026"
    uebung = antwort["exercises"][0]
    assert uebung["title"] == "Bankdruecken"
    assert float(uebung["month_a"]["best_weight"]) == 75.0
    assert float(uebung["month_b"]["best_weight"]) == 90.0
    assert float(uebung["delta"]["best_weight"]) == 15.0
    # Durchschnitte: (70+75)/2 = 72.50 und (85+90)/2 = 87.50
    assert float(uebung["month_a"]["avg_weight"]) == 72.50
    assert float(uebung["month_b"]["avg_weight"]) == 87.50
    assert uebung["month_a"]["avg_reps"] == 9.0
    assert uebung["month_b"]["avg_reps"] == 7.0
    assert uebung["delta"]["avg_reps"] == -2.0
    assert uebung["month_a"]["session_count"] == 1


def test_koerpergewichtsuebung_zeigt_wiederholungen(client: TestClient) -> None:
    """Klimmzuege haben kein Gewicht - Fortschritt sind die Wiederholungen."""
    ctx = _setup(client)
    alt = _workout(client, ctx, "2025-09-10T18:00:00Z")
    _satz(client, alt, ctx["klimmzug"], 5)
    _satz(client, alt, ctx["klimmzug"], 4)

    neu = _workout(client, ctx, "2026-04-10T18:00:00Z")
    _satz(client, neu, ctx["klimmzug"], 9)
    _satz(client, neu, ctx["klimmzug"], 8)

    antwort = client.get(
        f"{BASIS}/users/{ctx['user_id']}/log/progress",
        params={"month_a": "2025-09", "month_b": "2026-04"},
    ).json()
    uebung = antwort["exercises"][0]
    assert uebung["weighted"] is False
    assert uebung["month_a"]["best_weight"] is None
    assert uebung["month_a"]["avg_weight"] is None
    # beides: bester Satz und Durchschnitt
    assert uebung["month_a"]["best_reps"] == 5
    assert uebung["month_b"]["best_reps"] == 9
    assert uebung["delta"]["best_reps"] == 4
    assert uebung["month_a"]["avg_reps"] == 4.5
    assert uebung["month_b"]["avg_reps"] == 8.5


def test_custom_workouts_zaehlen_nicht_in_die_auswertung(client: TestClient) -> None:
    """Der Kern der Custom-Regel: in der Historie sichtbar, in der Auswertung nicht."""
    ctx = _setup(client)
    geplant = _workout(client, ctx, "2026-04-10T18:00:00Z")
    _satz(client, geplant, ctx["bank"], 8, 80)

    # Im Hotel improvisiert, mit deutlich leichteren Gewichten - wuerde den
    # Monatsschnitt nach unten ziehen.
    frei = _workout(client, ctx, "2026-04-20T18:00:00Z", custom=True)
    _satz(client, frei, ctx["bank"], 15, 30)

    antwort = client.get(
        f"{BASIS}/users/{ctx['user_id']}/log/progress",
        params={"month_a": "2026-03", "month_b": "2026-04"},
    ).json()
    uebung = antwort["exercises"][0]
    assert uebung["month_b"]["set_count"] == 1
    assert float(uebung["month_b"]["best_weight"]) == 80.0
    assert float(uebung["month_b"]["avg_weight"]) == 80.0
    assert antwort["excluded_custom_workouts"] == 1

    # in der Historie steht sie trotzdem
    log = client.get(f"{BASIS}/users/{ctx['user_id']}/log/workouts").json()
    assert len(log) == 2


def test_uebung_nur_in_einem_monat(client: TestClient) -> None:
    """Neu dazugekommene Uebungen duerfen nicht unsichtbar bleiben."""
    ctx = _setup(client)
    alt = _workout(client, ctx, "2025-09-10T18:00:00Z")
    _satz(client, alt, ctx["bank"], 8, 80)
    neu = _workout(client, ctx, "2026-04-10T18:00:00Z")
    _satz(client, neu, ctx["klimmzug"], 10)

    antwort = client.get(
        f"{BASIS}/users/{ctx['user_id']}/log/progress",
        params={"month_a": "2025-09", "month_b": "2026-04"},
    ).json()
    nach_titel = {u["title"]: u for u in antwort["exercises"]}

    assert nach_titel["Bankdruecken"]["month_b"] is None
    assert nach_titel["Bankdruecken"]["delta"]["best_weight"] is None
    assert nach_titel["Klimmzuege"]["month_a"] is None
    assert nach_titel["Klimmzuege"]["month_b"]["best_reps"] == 10


def test_ausgefallene_einheit_zaehlt_nicht(client: TestClient) -> None:
    ctx = _setup(client)
    ausgefallen = client.post(
        f"{BASIS}/workouts",
        json={
            "date": "2026-04-10T18:00:00Z",
            "workout_plan_id": ctx["plan_id"],
            "training_day_id": ctx["tag_id"],
            "attended": False,
        },
    ).json()["id"]
    _satz(client, ausgefallen, ctx["bank"], 8, 80)

    antwort = client.get(
        f"{BASIS}/users/{ctx['user_id']}/log/progress",
        params={"month_a": "2026-03", "month_b": "2026-04"},
    ).json()
    assert antwort["exercises"] == []


def test_monatsgrenze_liegt_in_lokaler_zeitzone(client: TestClient) -> None:
    """22:30 UTC am 31.03. ist in Europe/Berlin schon der 1. April.

    Ohne feste Zeitzone landete diese Einheit im Maerz und der Vergleich
    waere je nach Betrachter ein anderer.
    """
    ctx = _setup(client)
    spaet = _workout(client, ctx, "2026-03-31T22:30:00Z")
    _satz(client, spaet, ctx["bank"], 8, 80)

    monate = client.get(f"{BASIS}/users/{ctx['user_id']}/log/months").json()
    assert [m["month"] for m in monate] == ["2026-04"]


def test_unbekannter_user_und_kaputter_monat(client: TestClient) -> None:
    ctx = _setup(client)
    assert client.get(f"{BASIS}/users/9999/log/workouts").status_code == 404
    assert client.get(f"{BASIS}/users/9999/log/months").status_code == 404

    kaputt = client.get(
        f"{BASIS}/users/{ctx['user_id']}/log/progress",
        params={"month_a": "April", "month_b": "2026-04"},
    )
    assert kaputt.status_code == 422
    assert "April" in kaputt.json()["detail"]

    monat_dreizehn = client.get(
        f"{BASIS}/users/{ctx['user_id']}/log/progress",
        params={"month_a": "2026-13", "month_b": "2026-04"},
    )
    assert monat_dreizehn.status_code == 422
