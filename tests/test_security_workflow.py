import io, time, concurrent.futures
import cv2, numpy as np
from sqlalchemy import select, func
from backend.db import transaction
from backend.models import *
from backend.app import digest


def submit(client, accounts, key="event-key-123"):
    h = {**accounts["RTO"]["headers"], "Idempotency-Key": key}
    r = client.post(
        "/api/operator/manual",
        json={
            "plate": "GJ01AB1234",
            "type": "Signal Jump",
            "location": "Test junction",
            "explanation": "Observed prohibited crossing; operator photograph attached separately.",
        },
        headers=h,
    )
    assert r.status_code in (200, 201), r.json
    return r.json["id"]


def attach(client, accounts, cid):
    _, im = cv2.imencode(".jpg", np.full((300, 500, 3), 128, np.uint8))
    r = client.post(
        f"/api/candidates/{cid}/evidence",
        data=im.tobytes(),
        content_type="image/jpeg",
        headers=accounts["RTO"]["headers"],
    )
    assert r.status_code == 201, r.json


def confirm(client, accounts, cid):
    return client.post(
        f"/api/operator/candidates/{cid}/review",
        json={
            "decision": "CONFIRMED",
            "reason": "Evidence and relevant restrictions reviewed",
            "plate": "GJ01AB1234",
            "evidence_reviewed": True,
        },
        headers=accounts["RTO"]["headers"],
    )


def approve_link(client, accounts):
    r = client.post(
        "/api/user/vehicles/link",
        json={
            "plate": "GJ01AB1234",
            "proof": "Test registration certificate checked by operator",
        },
        headers=accounts["USER"]["headers"],
    )
    assert r.status_code == 201, r.json
    r = client.post(
        "/api/operator/ownership/" + r.json["id"] + "/review",
        json={
            "decision": "APPROVED",
            "reason": "Registration and identity checked",
            "proof_checked": True,
        },
        headers=accounts["RTO"]["headers"],
    )
    assert r.status_code == 200, r.json


def test_public_escalation_ingestion_and_json(client):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "a@test.dev",
            "password": "password1234",
            "full_name": "A",
            "role": "ADMIN",
        },
    )
    assert r.status_code == 403
    assert client.post("/addViolation", json={}).status_code == 401
    assert client.get("/unknown").status_code == 404
    assert client.post("/api/auth/register", data="{}").status_code == 415
    assert client.post("/api/auth/register", json=[]).status_code == 400


def test_unverified_plate_does_not_expose_records(client, accounts):
    cid = submit(client, accounts)
    attach(client, accounts, cid)
    assert confirm(client, accounts, cid).status_code == 200
    r = client.post(
        "/api/user/vehicles/link",
        json={"plate": "GJ01AB1234", "proof": "I typed a plate"},
        headers=accounts["USER"]["headers"],
    )
    assert r.status_code == 201
    assert (
        client.get("/api/user/memos", headers=accounts["USER"]["headers"]).json["total"]
        == 0
    )
    assert (
        client.get(
            "/api/candidates/" + cid, headers=accounts["USER"]["headers"]
        ).status_code
        == 404
    )
    assert (
        client.get(
            "/api/candidates/" + cid + "/evidence/0",
            headers=accounts["USER"]["headers"],
        ).status_code
        == 404
    )
    assert (
        client.get(
            "/api/operator/candidates", headers=accounts["USER"]["headers"]
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/api/operator/memos", headers=accounts["GOVT"]["headers"]
        ).status_code
        == 403
    )


def test_signup_plate_pending_and_staff_uses_database_role(client, accounts, app):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "new@test.dev",
            "password": "unique-password",
            "full_name": "New",
            "vehicle_number": "GJ01AB1234",
        },
    )
    assert r.status_code == 200
    h = {"Authorization": "Bearer " + r.json["access_token"]}
    assert client.get("/api/user/vehicles", headers=h).json[0]["status"] == "PENDING"
    with transaction(app.extensions["engine"]) as db:
        db.get(User, accounts["RTO"]["id"]).role = "USER"
    assert (
        client.get(
            "/api/operator/candidates", headers=accounts["RTO"]["headers"]
        ).status_code
        == 403
    )


def test_real_review_payment_and_dispute_workflow(client, accounts, app):
    approve_link(client, accounts)
    cid = submit(client, accounts)
    assert confirm(client, accounts, cid).status_code == 409
    attach(client, accounts, cid)
    assert confirm(client, accounts, cid).status_code == 200
    assert confirm(client, accounts, cid).status_code == 200
    memos = client.get("/api/user/memos", headers=accounts["USER"]["headers"]).json
    assert memos["total"] == 1
    m = memos["items"][0]
    assert m["fine_amount"] == 500
    assert (
        client.get(
            "/api/candidates/" + cid + "/evidence/0",
            headers=accounts["USER"]["headers"],
        ).status_code
        == 200
    )
    pdf = client.get(
        "/api/memos/" + m["id"] + "/pdf", headers=accounts["USER"]["headers"]
    )
    assert pdf.data.startswith(b"%PDF")
    assert (
        client.post(
            "/api/user/pay",
            json={"memo_id": m["id"]},
            headers=accounts["USER"]["headers"],
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/user/pay",
            json={"memo_id": m["id"], "mode": "SANDBOX", "acknowledge_no_money": True},
            headers=accounts["OTHER"]["headers"],
        ).status_code
        == 404
    )
    d = client.post(
        "/api/user/disputes",
        json={"memo_id": m["id"], "reason": "I dispute the evidence context"},
        headers=accounts["USER"]["headers"],
    )
    assert d.status_code == 201
    _, support = cv2.imencode(".jpg", np.full((200, 300, 3), 150, np.uint8))
    endpoint = "/api/disputes/" + d.json["id"] + "/evidence"
    assert (
        client.post(
            endpoint,
            data=support.tobytes(),
            content_type="image/jpeg",
            headers=accounts["USER"]["headers"],
        ).status_code
        == 201
    )
    assert (
        client.get(endpoint + "/0", headers=accounts["OTHER"]["headers"]).status_code
        == 404
    )
    assert (
        client.get(endpoint + "/0", headers=accounts["RTO"]["headers"]).status_code
        == 200
    )
    assert (
        client.post(
            "/api/user/pay",
            json={"memo_id": m["id"], "mode": "SANDBOX", "acknowledge_no_money": True},
            headers=accounts["USER"]["headers"],
        ).status_code
        == 409
    )
    r = client.post(
        "/api/operator/disputes/" + d.json["id"] + "/review",
        json={"decision": "DISMISSED", "reason": "Evidence establishes context"},
        headers=accounts["RTO"]["headers"],
    )
    assert r.status_code == 200
    payload = {"memo_id": m["id"], "mode": "SANDBOX", "acknowledge_no_money": True}
    pay = client.post(
        "/api/user/pay", json=payload, headers=accounts["USER"]["headers"]
    )
    assert pay.status_code == 201, pay.json
    again = client.post(
        "/api/user/pay", json=payload, headers=accounts["USER"]["headers"]
    )
    assert again.json["id"] == pay.json["id"]
    stats = client.get("/api/gov/analytics", headers=accounts["GOVT"]["headers"]).json
    assert stats["kpi"]["total_revenue"] == 500
    assert stats["kpi"]["verified_real_revenue"] == 0
    with transaction(app.extensions["engine"]) as db:
        assert db.scalar(select(func.count()).select_from(Violation)) == 1
        assert db.scalar(select(func.count()).select_from(Payment)) == 1
        n = db.scalar(select(Outbox))
        assert n.status == "PREVIEW"
        assert "localhost:3000/dashboard" in n.body


def test_idempotency_and_concurrent_confirmation(client, accounts, app):
    cid = submit(client, accounts)
    assert submit(client, accounts) == cid
    attach(client, accounts, cid)

    def run(_):
        with app.test_client() as c:
            return confirm(c, accounts, cid).status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(run, range(2))) == [200, 200]
    with transaction(app.extensions["engine"]) as db:
        assert db.scalar(select(func.count()).select_from(Memo)) == 1


def test_revoke_and_profile_password_require_current(client, accounts):
    h = accounts["USER"]["headers"]
    assert (
        client.put(
            "/api/user/profile",
            json={
                "full_name": "User",
                "password": "new-password-123",
                "current_password": "wrong",
            },
            headers=h,
        ).status_code
        == 403
    )
    assert client.post("/api/auth/logout", headers=h).status_code == 200
    assert client.get("/api/auth/me", headers=h).status_code == 401


def test_device_scoping_and_replay(client, accounts, app):
    c = client.post(
        "/api/operator/cameras",
        json={"name": "Device camera", "location": "Test", "config": {}},
        headers=accounts["ADMIN"]["headers"],
    ).json
    d = client.post(
        "/api/admin/devices",
        json={"camera_id": c["id"]},
        headers=accounts["ADMIN"]["headers"],
    ).json
    payload = {
        "device_id": d["id"],
        "event_id": "capture-123",
        "captured_at": now(),
        "type": "Signal Jump",
        "explanation": "Device crossing candidate",
        "plate": "",
    }
    assert client.post("/api/device/candidates", json=payload).status_code == 403
    h = {"X-Device-Token": d["token"]}
    r = client.post("/api/device/candidates", json=payload, headers=h)
    assert r.status_code == 201
    assert (
        client.post("/api/device/candidates", json=payload, headers=h).json["id"]
        == r.json["id"]
    )
    with transaction(app.extensions["engine"]) as db:
        assert db.scalar(select(func.count()).select_from(Memo)) == 0
    client.delete("/api/admin/devices/" + d["id"], headers=accounts["ADMIN"]["headers"])
    assert (
        client.post("/api/device/candidates", json=payload, headers=h).status_code
        == 403
    )


def test_rollback_releases_connection(app):
    try:
        with transaction(app.extensions["engine"]) as db:
            db.add(
                User(
                    email="rollback@test.dev",
                    full_name="Rollback",
                    password_hash="not-used",
                    role="USER",
                )
            )
            db.flush()
            raise RuntimeError("Injected failure")
    except RuntimeError:
        pass
    with transaction(app.extensions["engine"]) as db:
        assert not db.scalar(select(User).where(User.email == "rollback@test.dev"))
