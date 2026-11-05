import hashlib
from backend.db import transaction
from backend.models import (
    Candidate,
    CaseMetadata,
    DatasetAsset,
    VehicleProfile,
    Link,
    Violation,
    Memo,
)


def fixture(app, accounts):
    with transaction(app.extensions["engine"]) as db:
        db.add(
            VehicleProfile(
                id="GJ00DM1001",
                model="Fictional scooter",
                is_demo=1,
                owner_display_name="Fictional owner",
            )
        )
        db.add(
            VehicleProfile(
                id="GJ00DM1010",
                model="Fictional scooter",
                vehicle_class="motorcycle",
                is_demo=1,
            )
        )
        db.add(
            Link(user_id=accounts["USER"]["id"], plate="GJ00DM1001", status="APPROVED")
        )
        db.add(
            DatasetAsset(
                id="test-photo",
                title="Test evidence",
                category="helmet_safety",
                source_url="https://example.test/source",
                license="Test fixture",
                attribution="Synthetic test fixture",
                object_key="datasets/test.jpg",
                sha256=hashlib.sha256(b"test").hexdigest(),
                annotations={"labels": []},
            )
        )
        for ident, kind in [("demo-case", True), ("recorded-case", False)]:
            db.add(
                Candidate(
                    id=ident,
                    event_key=ident,
                    rule="Helmet Violation",
                    location="Test junction",
                    plate="GJ00DM1001",
                    status="CONFIRMED",
                    explanation="Private identifying explanation",
                    created_at="2026-11-04T20:00:00+00:00",
                )
            )
            db.flush()
            db.add(CaseMetadata(id=ident, is_demo=int(kind)))
            db.add(
                Violation(
                    id="v-" + ident,
                    candidate_id=ident,
                    plate="GJ00DM1001",
                    rule="Helmet Violation",
                    location="Test junction",
                )
            )
            db.flush()
            db.add(
                Memo(
                    id="m-" + ident,
                    violation_id="v-" + ident,
                    fine_amount=100,
                    status="SANDBOX_PAID" if kind else "UNPAID",
                )
            )


def test_shared_totals_filters_and_citizen_ownership(app, client, accounts):
    fixture(app, accounts)
    for role in ["USER", "RTO", "ADMIN", "GOVT"]:
        h = accounts[role]["headers"]
        for scope, total in [("all", 2), ("demo", 1), ("live", 1)]:
            cases = client.get("/api/cases?scope=" + scope, headers=h).json
            overview = client.get("/api/overview?scope=" + scope, headers=h).json
            assert cases["total"] == overview["total"] == total
    h = accounts["OTHER"]["headers"]
    assert client.get("/api/cases", headers=h).json["total"] == 0
    assert client.get("/api/cases/demo-case", headers=h).status_code == 404
    memos = client.get(
        "/api/user/memos?status=UNPAID", headers=accounts["USER"]["headers"]
    ).json
    assert memos["total"] == 1 and memos["items"][0]["status"] == "UNPAID"


def test_government_redaction_and_ist_boundary(app, client, accounts):
    fixture(app, accounts)
    h = accounts["GOVT"]["headers"]
    data = client.get("/api/cases/demo-case", headers=h).json
    assert data["plate"] is data["vehicle"] is data["reviewer"] is None
    assert data["evidence"] == [] and data["observations"] == {} and data["ocr"] == []
    assert "Private identifying" not in str(data)
    assert client.get("/api/registry", headers=h).status_code == 403
    result = client.get(
        "/api/overview?from=2026-11-05T00:00:00%2B05:30&to=2026-11-06T00:00:00%2B05:30",
        headers=h,
    ).json
    assert result["total"] == 2
    assert result["trend"] == [{"date": "2026-11-05", "cases": 2}]


def test_dataset_import_is_local_idempotent_and_fictional_only(app, client, accounts):
    fixture(app, accounts)
    h = {**accounts["RTO"]["headers"], "Idempotency-Key": "test-import-one"}
    a = client.post("/api/datasets/test-photo/example", json={}, headers=h)
    assert a.status_code == 201
    b = client.post("/api/datasets/test-photo/example", json={}, headers=h)
    assert b.status_code == 200 and a.json == b.json
    assert client.get("/api/cases/" + a.json["id"], headers=h).json["is_demo"] is True
    assert (
        client.post(
            "/api/datasets/test-photo/example", json={"plate": "GJ01AB1234"}, headers=h
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/datasets/test-photo/example",
            json={},
            headers=accounts["USER"]["headers"],
        ).status_code
        == 403
    )
    app.config["APP_ENV"] = "production"
    assert (
        client.post("/api/datasets/test-photo/example", json={}, headers=h).status_code
        == 403
    )


def test_display_reference_search_preserves_role_privacy(app, client, accounts):
    fixture(app, accounts)
    reference = "EM-" + hashlib.sha256(b"demo-case").hexdigest()[:7].upper()
    for role in ["RTO", "USER", "GOVT"]:
        response = client.get(
            "/api/cases?q=" + reference, headers=accounts[role]["headers"]
        )
        assert response.status_code == 200 and response.json["total"] == 1
        assert response.json["items"][0]["id"] == "demo-case"
        assert (
            client.get(
                "/api/cases?q=" + reference.lower(), headers=accounts[role]["headers"]
            ).json["total"]
            == 1
        )
    assert (
        client.get(
            "/api/cases?q=" + reference, headers=accounts["OTHER"]["headers"]
        ).json["total"]
        == 0
    )


def test_filter_choices_are_scoped_and_research_routes_are_removed(
    app, client, accounts
):
    fixture(app, accounts)
    for role in ["RTO", "USER", "GOVT"]:
        response = client.get("/api/case-filters", headers=accounts[role]["headers"])
        assert response.status_code == 200
        assert response.json == {
            "locations": ["Test junction"],
            "types": ["Helmet Violation"],
        }
    response = client.get("/api/case-filters", headers=accounts["OTHER"]["headers"])
    assert response.json == {"locations": [], "types": []}
    assert (
        client.post(
            "/api/datasets/test-photo/analysis",
            json={},
            headers=accounts["RTO"]["headers"],
        ).status_code
        == 404
    )
    assert client.post("/api/auth/reset", json={}).status_code == 404
