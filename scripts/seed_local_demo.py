"""Explicit, local-only test accounts/fixtures. Never runs during production startup."""

import argparse, json, os, secrets
from pathlib import Path
import cv2
import numpy as np
from dotenv import load_dotenv
from sqlalchemy import select
from werkzeug.security import generate_password_hash, check_password_hash
from backend.db import make_engine, initialize, transaction
from backend.models import (
    User,
    Link,
    Camera,
    Candidate,
    Violation,
    Memo,
    Payment,
    Dispute,
    Outbox,
    Audit,
    now,
)
from backend.storage import Storage
from backend.rules import validate_config

ROOT = Path(__file__).resolve().parents[1]
ROLES = {
    "RTO": ("rto.demo@preksha.test", "Demo RTO Officer"),
    "GOVT": ("govt.demo@preksha.test", "Demo Government Analyst"),
    "ADMIN": ("admin.demo@preksha.test", "Demo Administrator"),
    "USER": ("citizen.demo@preksha.test", "Demo Vehicle Owner"),
    "OTHER": ("other.demo@preksha.test", "Second Demo Owner"),
}


def seed(data_dir, access_from=None):
    load_dotenv(ROOT / ".env", override=False)
    if os.getenv("APP_ENV", "local") != "local" or os.getenv("DATABASE_URL"):
        raise RuntimeError(
            "Demo seeding is allowed only in local SQLite mode with DATABASE_URL unset"
        )
    data_dir = Path(data_dir).resolve()
    if not data_dir.is_relative_to(ROOT / "data"):
        raise RuntimeError("Use a data folder inside this project")
    data_dir.mkdir(parents=True, exist_ok=True)
    access_file = data_dir / "test-access.json"
    source = Path(access_from) if access_from else access_file
    access = (
        json.loads(source.read_text(encoding="utf-8-sig"))
        if source.exists()
        else {
            role: {
                "email": email,
                "password": "Prk!" + role + "-" + secrets.token_hex(6),
            }
            for role, (email, _) in ROLES.items()
        }
    )
    for role, (email, _) in ROLES.items():
        if access[role]["email"] != email or len(access[role]["password"]) < 12:
            raise ValueError("Unexpected local test credential file")
    engine = make_engine("sqlite:///" + (data_dir / "traffic.db").as_posix())
    initialize(engine)
    storage = Storage({"DATA_DIR": str(data_dir), "STORAGE_MODE": "local"})
    # A clearly labeled synthetic evidence card, never represented as AI output.
    image = np.full((480, 800, 3), 245, np.uint8)
    for i, line in enumerate(
        [
            "SYNTHETIC TEST EVIDENCE",
            "College demonstration fixture",
            "NOT a real traffic offence",
            "Plate: GJ00DM1001",
            "No object recognition performed on this card",
        ]
    ):
        cv2.putText(
            image,
            line,
            (30, 70 + i * 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (30, 50, 100),
            2,
        )
    _, encoded = cv2.imencode(".jpg", image)
    evidence = storage.put("demo-fixtures/synthetic-evidence.jpg", encoded.tobytes())
    counts = {"accounts_created": 0, "memos_created": 0, "candidates_created": 0}
    with transaction(engine) as db:
        users = {}
        for role, (email, name) in ROLES.items():
            user = db.scalar(select(User).where(User.email == email))
            if user:
                if not check_password_hash(
                    user.password_hash, access[role]["password"]
                ):
                    raise RuntimeError(
                        "A test password was changed; existing credentials were preserved. Use the local recovery command if needed."
                    )
            else:
                user = User(
                    id="demo-" + role.lower(),
                    email=email,
                    full_name=name,
                    role="USER" if role == "OTHER" else role,
                    password_hash=generate_password_hash(access[role]["password"]),
                )
                db.add(user)
                db.flush()
                counts["accounts_created"] += 1
            users[role] = user
        for ident, who, plate, status in [
            ("demo-owner-primary", "USER", "GJ00DM1001", "APPROVED"),
            ("demo-owner-pending", "USER", "GJ00DM1002", "PENDING"),
            ("demo-owner-other", "OTHER", "GJ00DM2001", "APPROVED"),
        ]:
            if not db.get(Link, ident):
                db.add(
                    Link(
                        id=ident,
                        user_id=users[who].id,
                        plate=plate,
                        status=status,
                        proof="SYNTHETIC LOCAL TEST registration fixture; not a real government record",
                        reviewer=users["RTO"].id if status == "APPROVED" else None,
                        reason=(
                            "Local demonstration ownership only"
                            if status == "APPROVED"
                            else None
                        ),
                    )
                )
        if not db.get(Camera, "demo-camera"):
            db.add(
                Camera(
                    id="demo-camera",
                    name="Demo prerecorded traffic camera",
                    location="LOCAL TEST junction",
                    config=validate_config(
                        {
                            "enabled": ["restricted_zone"],
                            "restricted_zone": [[0, 0.8], [1, 0.8], [1, 1], [0, 1]],
                            "context_confirmed": True,
                            "resolution": [1920, 1080],
                        }
                    ),
                )
            )
        db.flush()
        cases = [
            ("unpaid", "Signal Jump", 500, "UNPAID", "USER"),
            ("paid", "Speeding", 1000, "SANDBOX_PAID", "USER"),
            ("disputed", "Parking Violation", 200, "DISPUTED", "USER"),
            ("other", "Signal Jump", 500, "UNPAID", "OTHER"),
        ]
        for label, rule, amount, status, who in cases:
            cid = "demo-event-" + label
            vid = "demo-violation-" + label
            mid = "demo-memo-" + label
            plate = "GJ00DM2001" if who == "OTHER" else "GJ00DM1001"
            if not db.get(Candidate, cid):
                db.add(
                    Candidate(
                        id=cid,
                        event_key=cid,
                        camera_id="demo-camera",
                        rule=rule,
                        location="LOCAL TEST junction",
                        model_version="synthetic-demo-fixture-NO-INFERENCE",
                        status="CONFIRMED",
                        plate=plate,
                        explanation="SYNTHETIC LOCAL TEST: pre-created demonstration case, not a detected real offence.",
                        observations={
                            "mode": "SYNTHETIC_TEST_FIXTURE",
                            "not_real_enforcement": True,
                        },
                        evidence=[evidence],
                        reviewer=users["RTO"].id,
                        review_reason="Explicitly seeded fictional test scenario",
                    )
                )
                db.flush()
                counts["candidates_created"] += 1
            if not db.get(Violation, vid):
                db.add(
                    Violation(
                        id=vid,
                        candidate_id=cid,
                        plate=plate,
                        rule=rule,
                        location="LOCAL TEST junction",
                    )
                )
                db.flush()
            if not db.get(Memo, mid):
                db.add(
                    Memo(
                        id=mid,
                        violation_id=vid,
                        fine_amount=amount,
                        status=status,
                        payment_date=now() if status == "SANDBOX_PAID" else None,
                    )
                )
                db.flush()
                counts["memos_created"] += 1
                db.add(
                    Audit(
                        actor="explicit-local-demo-seed",
                        action="SEED_SYNTHETIC_CASE",
                        target=cid,
                        details={"memo": mid, "synthetic": True},
                    )
                )
            if label == "paid" and not db.get(Payment, "demo-receipt"):
                db.add(
                    Payment(
                        id="demo-receipt",
                        memo_id=mid,
                        user_id=users[who].id,
                        amount=amount,
                    )
                )
            if label == "disputed" and not db.get(Dispute, "demo-dispute"):
                db.add(
                    Dispute(
                        id="demo-dispute",
                        memo_id=mid,
                        user_id=users[who].id,
                        reason="SYNTHETIC TEST: please review this demonstration parking memo.",
                    )
                )
            if not db.get(Outbox, "demo-notice-" + label):
                db.add(
                    Outbox(
                        id="demo-notice-" + label,
                        memo_id=mid,
                        recipient=users[who].email,
                        status="PREVIEW",
                        body=f"LOCAL TEST MEMO {mid}\nSynthetic demonstration only. No actual notice or payment.",
                    )
                )
        for label, status, refs in [
            ("pending", "PENDING", [evidence]),
            ("needs-evidence", "NEEDS_EVIDENCE", []),
        ]:
            cid = "demo-review-" + label
            if not db.get(Candidate, cid):
                db.add(
                    Candidate(
                        id=cid,
                        event_key=cid,
                        camera_id="demo-camera",
                        rule="Signal Jump",
                        location="LOCAL TEST junction",
                        model_version="synthetic-demo-fixture-NO-INFERENCE",
                        status=status,
                        plate="GJ00DM1001" if label == "pending" else None,
                        explanation="SYNTHETIC LOCAL TEST review exercise. Confirm, reject or request evidence with a reason.",
                        observations={
                            "mode": "SYNTHETIC_TEST_FIXTURE",
                            "not_real_enforcement": True,
                        },
                        evidence=refs,
                    )
                )
                counts["candidates_created"] += 1
    access_file.write_text(json.dumps(access, indent=2), encoding="utf-8")
    table = ["| Portal | Email | Password |", "|---|---|---|"]
    for role in ROLES:
        table.append(
            f'| {role if role!="OTHER" else "Second citizen"} | {access[role]["email"]} | `{access[role]["password"]}` |'
        )
    guide = (
        """# Local test accounts and sample records

These accounts are for the local demonstration database only. They are never
created automatically in production. Demo identities and owner associations are
fictional. The base seed uses synthetic cards; the showcase adds attributed real
dataset imagery with clearly labeled practice scenarios. No real notices or payments.

Open http://127.0.0.1:3001 for the currently running preview. Sign out before
switching roles. The landing page has separate Vehicle Owner, RTO, Government and
Administrator portals. These passwords persist across ordinary restarts.

"""
        + "\n".join(table)
        + """

Starting base examples: GJ00DM1001 has unpaid INR 500, sandbox-paid INR 1000 and
disputed INR 200 memos. GJ00DM1002 starts with pending ownership. Showcase also
adds the primary owner's fictional GJ00DM1010 scooter and additional cases.
The second citizen owns GJ00DM2001 and GJ00DM2010 after showcase setup; their
records remain private from the first citizen. Your later decisions/payments
change these initial statuses and are preserved.

Preserved project database: data/traffic.db. Double-click START_PROJECT.cmd to
run the saved build at http://127.0.0.1:3001. See EVENING_GUIDE.md for the tour.
Do not publish this credentials file, the private data folder or saved-backups.
"""
    )
    (ROOT / "LOCAL_TEST_ACCOUNTS.md").write_text(guide, encoding="utf-8")
    engine.dispose()
    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=str(ROOT / "data"))
    parser.add_argument("--access-from")
    parser.add_argument("--verify-api", action="store_true")
    args = parser.parse_args()
    print(json.dumps(seed(args.data_dir, args.access_from)))
    if args.verify_api:
        import httpx

        access = json.loads(
            (Path(args.data_dir) / "test-access.json").read_text(encoding="utf-8")
        )
        with httpx.Client(
            base_url="http://127.0.0.1:5000", timeout=20, trust_env=False
        ) as client:
            for role, credentials in access.items():
                response = client.post("/api/auth/login", json=credentials)
                response.raise_for_status()
                result = response.json()
                expected = "USER" if role == "OTHER" else role
                assert result["user"]["role"] == expected
                headers = {"Authorization": "Bearer " + result["access_token"]}
                route = {
                    "RTO": "/api/operator/candidates?size=100",
                    "GOVT": "/api/gov/analytics",
                    "ADMIN": "/api/admin/users",
                    "USER": "/api/user/memos?size=100",
                    "OTHER": "/api/user/memos?size=100",
                }[role]
                response = client.get(route, headers=headers)
                response.raise_for_status()
                data = response.json()
                if role in ("USER", "OTHER"):
                    ids = {r["id"] for r in data["items"]}
                    assert (
                        {"demo-memo-unpaid", "demo-memo-paid", "demo-memo-disputed"}
                        if role == "USER"
                        else {"demo-memo-other"}
                    ).issubset(ids)
                    if role == "USER":
                        assert (
                            client.get(
                                "/api/candidates/demo-event-other", headers=headers
                            ).status_code
                            == 404
                        )
                if role == "GOVT":
                    assert data["kpi"]["total_revenue"] >= 1000
                print(role + ": login and portal data verified")


if __name__ == "__main__":
    main()
