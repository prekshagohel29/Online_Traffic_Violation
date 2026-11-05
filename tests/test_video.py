import time
from pathlib import Path
import pytest, cv2, numpy as np
from sqlalchemy import select, func
from backend.models import *
from backend.db import transaction
from backend.worker import Worker
from backend.vision import Detector, process_frame


def camera(client, accounts):
    config = {
        "enabled": ["restricted_zone"],
        "restricted_zone": [[0, 0.8], [1, 0.8], [1, 1], [0, 1]],
        "context_confirmed": True,
        "resolution": [1920, 1080],
    }
    r = client.post(
        "/api/operator/cameras",
        json={
            "name": "Sample view",
            "location": "CC0 sample demonstration",
            "config": config,
        },
        headers=accounts["RTO"]["headers"],
    )
    assert r.status_code == 201, r.json
    return r.json["id"]


def test_upload_validation_cancellation_and_missing_model(client, accounts, app):
    cid = camera(client, accounts)
    h = accounts["RTO"]["headers"]
    assert (
        client.post(
            "/api/operator/sessions",
            json={"camera_id": cid, "kind": "webcam"},
            headers=h,
        ).status_code
        == 503
    )
    assert (
        client.post(
            "/api/operator/uploads",
            json={"camera_id": cid, "filename": "bad.exe", "size": 200},
            headers=h,
        ).status_code
        == 400
    )
    ticket = client.post(
        "/api/operator/uploads",
        json={"camera_id": cid, "filename": "bad.mp4", "size": 200},
        headers=h,
    ).json
    assert client.put(ticket["upload_url"], data=b"x" * 201).status_code == 400
    assert client.put(ticket["upload_url"], data=b"x" * 200).status_code == 200
    assert client.put(ticket["upload_url"], data=b"x" * 200).status_code == 409
    assert (
        client.post(
            "/api/operator/jobs/" + ticket["job_id"] + "/submit", headers=h
        ).status_code
        == 202
    )
    worker = Worker(app)
    worker.detector.net = None
    worker.detector.error = "Object model unavailable"
    worker.tick()
    jobs = client.get("/api/operator/jobs", headers=h).json["items"]
    assert jobs[0]["status"] == "FAILED"
    assert "unavailable" in jobs[0]["error"]
    ticket = client.post(
        "/api/operator/uploads",
        json={"camera_id": cid, "filename": "bad.mp4", "size": 200},
        headers=h,
    ).json
    assert (
        client.post(
            "/api/operator/jobs/" + ticket["job_id"] + "/cancel", headers=h
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/operator/jobs/" + ticket["job_id"] + "/submit", headers=h
        ).status_code
        == 409
    )


def test_frame_replay_backpressure_and_session_ownership(client, accounts, app):
    cid = camera(client, accounts)
    with transaction(app.extensions["engine"]) as db:
        db.add(
            Service(
                id="test-worker", heartbeat=time.time(), details={"model_ready": True}
            )
        )
    h = accounts["RTO"]["headers"]
    s = client.post(
        "/api/operator/sessions", json={"camera_id": cid, "kind": "webcam"}, headers=h
    ).json
    _, encoded = cv2.imencode(".jpg", np.zeros((300, 500, 3), np.uint8))
    payload = encoded.tobytes()

    def frame(seq, stamp):
        return client.post(
            "/api/operator/sessions/" + s["id"] + "/frames",
            data=payload,
            headers={
                **h,
                "Content-Type": "image/jpeg",
                "X-Sequence": str(seq),
                "X-Source-Time": str(stamp),
            },
        )

    assert frame(1, 1).status_code == 202
    assert frame(1, 1).status_code == 409
    assert frame(2, 2).status_code == 429
    with transaction(app.extensions["engine"]) as db:
        db.get(VideoSession, s["id"]).heartbeat = 0
    assert frame(2, 2).status_code == 202
    with transaction(app.extensions["engine"]) as db:
        assert (
            db.scalar(
                select(func.count()).select_from(Job).where(Job.status == "QUEUED")
            )
            == 1
        )
        assert db.get(VideoSession, s["id"]).dropped == 1
    assert (
        client.get(
            "/api/operator/sessions/" + s["id"], headers=accounts["USER"]["headers"]
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/operator/sessions/" + s["id"] + "/stop", headers=h
        ).status_code
        == 200
    )
    assert frame(3, 3).status_code == 409


def test_calibration_version_stops_existing_source(client, accounts, app):
    cid = camera(client, accounts)
    with transaction(app.extensions["engine"]) as db:
        db.add(
            Service(
                id="test-worker", heartbeat=time.time(), details={"model_ready": True}
            )
        )
    h = accounts["RTO"]["headers"]
    s = client.post(
        "/api/operator/sessions", json={"camera_id": cid, "kind": "webcam"}, headers=h
    ).json
    r = client.put(
        "/api/operator/cameras/" + cid,
        json={"name": "Changed", "location": "Test", "version": 1, "config": {}},
        headers=h,
    )
    assert r.status_code == 200
    assert (
        client.get("/api/operator/sessions/" + s["id"], headers=h).json["status"]
        == "CALIBRATION_CHANGED"
    )
    assert (
        client.put(
            "/api/operator/cameras/" + cid,
            json={"name": "Changed", "location": "Test", "version": 1, "config": {}},
            headers=h,
        ).status_code
        == 409
    )


@pytest.mark.skipif(
    not Path("models/yolox.onnx").exists()
    or not Path("samples/rush-hour.webm").exists(),
    reason="Run scripts.fetch_assets first",
)
def test_real_upload_to_review_memo_and_citizen(client, accounts, app):
    cid = camera(client, accounts)
    h = accounts["RTO"]["headers"]
    video = Path("samples/rush-hour.webm").read_bytes()
    ticket = client.post(
        "/api/operator/uploads",
        json={"camera_id": cid, "filename": "rush-hour.webm", "size": len(video)},
        headers=h,
    ).json
    assert client.put(ticket["upload_url"], data=video).status_code == 200
    assert (
        client.post(
            "/api/operator/jobs/" + ticket["job_id"] + "/submit", headers=h
        ).status_code
        == 202
    )
    worker = Worker(app)
    assert worker.detector.ready
    worker.tick()
    with transaction(app.extensions["engine"]) as db:
        j = db.get(Job, ticket["job_id"])
        assert j.status == "COMPLETED", j.error
        s = db.get(VideoSession, ticket["session_id"])
        assert s.processed >= 30
        assert s.result["tracks"]
        assert s.result["latency_ms"] > 0
        candidates = list(
            db.scalars(select(Candidate).where(Candidate.session_id == s.id))
        )
        assert (
            candidates
        ), "Expected entry into deliberately configured demonstration zone"
        candidate = candidates[0]
        assert candidate.evidence
        assert candidate.model_version.startswith("opencv-zoo")
    # Human supplies the college fixture plate after reviewing real image evidence. It is not an OCR prediction.
    link = client.post(
        "/api/user/vehicles/link",
        json={"plate": "GJ01AB1234", "proof": "College test registration fixture"},
        headers=accounts["USER"]["headers"],
    ).json
    assert (
        client.post(
            "/api/operator/ownership/" + link["id"] + "/review",
            json={
                "decision": "APPROVED",
                "reason": "Test ownership fixture verified",
                "proof_checked": True,
            },
            headers=h,
        ).status_code
        == 200
    )
    r = client.post(
        "/api/operator/candidates/" + candidate.id + "/review",
        json={
            "decision": "CONFIRMED",
            "reason": "Deliberately configured demonstration zone reviewed; not a claim of an actual illegal act",
            "plate": "GJ01AB1234",
            "evidence_reviewed": True,
        },
        headers=h,
    )
    assert r.status_code == 200, r.json
    m = client.get("/api/user/memos", headers=accounts["USER"]["headers"]).json
    assert m["total"] == 1
    assert (
        client.get(
            "/api/candidates/" + candidate.id + "/evidence/0",
            headers=accounts["USER"]["headers"],
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/user/pay",
            json={
                "memo_id": m["items"][0]["id"],
                "mode": "SANDBOX",
                "acknowledge_no_money": True,
            },
            headers=accounts["USER"]["headers"],
        ).status_code
        == 201
    )
    # A fresh app/engine reads persisted state after simulated process restart.
    from backend.app import create_app
    from backend.db import initialize

    restarted = create_app(
        {
            "DATA_DIR": app.config["DATA_DIR"],
            "JWT_SECRET_KEY": app.config["JWT_SECRET_KEY"],
            "DATABASE_URL": "",
        }
    )
    with transaction(restarted.extensions["engine"]) as db:
        assert db.scalar(select(func.count()).select_from(Payment)) == 1
    restarted.extensions["engine"].dispose()
