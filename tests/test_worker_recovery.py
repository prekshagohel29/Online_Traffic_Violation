import time
from sqlalchemy import select
from backend.db import transaction
from backend.worker import Worker
from backend.models import *


def test_interrupted_job_lease_is_reclaimed_with_bound(app, accounts):
    with transaction(app.extensions["engine"]) as db:
        c = Camera(name="Recovery camera", location="Test", config={})
        db.add(c)
        db.flush()
        s = VideoSession(
            user_id=accounts["RTO"]["id"],
            camera_id=c.id,
            kind="upload",
            config={},
            calibration_version=1,
        )
        db.add(s)
        db.flush()
        j = Job(
            user_id=accounts["RTO"]["id"],
            session_id=s.id,
            kind="upload",
            status="RUNNING",
            lease_owner="lost-worker",
            lease_until=time.time() - 1,
            attempts=1,
        )
        db.add(j)
        db.flush()
        ident = j.id
    worker = Worker(app)
    job = worker.claim()
    assert job.id == ident
    assert job.attempts == 2
    assert job.lease_owner == worker.id
    assert worker.claim() is None
    with transaction(app.extensions["engine"]) as db:
        j = db.get(Job, ident)
        j.lease_until = time.time() - 1
        j.attempts = 3
    assert worker.claim() is None
    with transaction(app.extensions["engine"]) as db:
        assert db.get(Job, ident).status == "FAILED"


def test_outbox_never_claims_delivery_without_setup(app, accounts):
    # Test sink: no SMTP/network call is enabled.
    with transaction(app.extensions["engine"]) as db:
        v = Violation(rule="Signal Jump", location="Test")
        db.add(v)
        db.flush()
        m = Memo(violation_id=v.id, fine_amount=500)
        db.add(m)
        db.flush()
        n = Outbox(
            memo_id=m.id,
            recipient="unverified@example.test",
            body="Test only",
            status="QUEUED",
        )
        db.add(n)
        db.flush()
        ident = n.id
    worker = Worker(app)
    worker.notify()
    with transaction(app.extensions["engine"]) as db:
        n = db.get(Outbox, ident)
        assert n.status == "FAILED"
        assert n.attempts == 1
        assert n.next_attempt > time.time()
