"""Explicit initialization/provisioning/import commands. Never contacts a default remote DB."""

import argparse, getpass, os, json
from pathlib import Path
from sqlalchemy import MetaData, Table, select, inspect
from werkzeug.security import generate_password_hash
from .app import create_app, plate
from .db import initialize, transaction
from .models import (
    User,
    Link,
    Candidate,
    Violation,
    Memo,
    Audit,
    Setting,
    Job,
    VideoSession,
    now,
)


def import_legacy(engine):
    names = set(inspect(engine).get_table_names())
    metadata = MetaData()

    def rows(name):
        if name not in names:
            return []
        table = Table(name, metadata, autoload_with=engine)
        with engine.connect() as connection:
            return [dict(r) for r in connection.execute(select(table)).mappings()]

    users = rows("users")
    vehicles = {str(x["vehicle_id"]): x for x in rows("vehicle")}
    links = rows("user_vehicles")
    violations = rows("violation")
    memo_rows = [("memo", x) for x in rows("memo")] + [
        ("fine", x) for x in rows("fine")
    ]

    def iso(value):
        return (
            value.isoformat()
            if hasattr(value, "isoformat")
            else str(value) if value is not None else now()
        )

    def safe_json(value):
        return json.loads(json.dumps(value, default=str))

    with transaction(engine) as db:
        if db.get(Setting, "legacy_import_v1"):
            return {"already_imported": True}
        for raw in users:
            ident = str(raw["user_id"])
            email = raw["email"].lower()
            demo = email.endswith("@system.com")
            if not db.get(User, ident):
                db.add(
                    User(
                        id=ident,
                        email=email,
                        password_hash=raw["password_hash"],
                        role=raw.get("role", "USER"),
                        full_name=raw.get("full_name") or email.split("@")[0],
                        phone_number=raw.get("phone_number") or "",
                        last_login=iso(raw.get("last_login")),
                        active=0 if demo else 1,
                        token_version=1,
                    )
                )
        db.flush()
        for raw in links:
            vehicle = vehicles.get(str(raw["vehicle_id"]))
            user_id = str(raw["user_id"])
            if vehicle and db.get(User, user_id):
                db.add(
                    Link(
                        user_id=user_id,
                        plate=vehicle["plate_number"],
                        proof="Legacy link — unverified; submit a new proof reference for RTO review",
                        reason="Reverification required before citizen access",
                    )
                )
        for raw in violations:
            ident = str(raw["violation_id"])
            vehicle = vehicles.get(str(raw["vehicle_id"]))
            c_id = "legacy-" + ident
            if db.get(Violation, ident):
                continue
            db.add(
                Candidate(
                    id=c_id,
                    event_key=c_id,
                    rule=raw["violation_type"],
                    location=raw["location"],
                    created_at=iso(raw.get("date_time")),
                    captured_at=iso(raw.get("date_time")),
                    explanation="Imported legacy violation. Historical verification cannot be established from the old schema.",
                    status="LEGACY_UNVERIFIED",
                    plate=vehicle["plate_number"] if vehicle else None,
                    model_version="legacy-unknown",
                    observations={
                        "legacy": safe_json(raw),
                        "evidence_status": "Missing in original schema",
                    },
                )
            )
            db.flush()
            db.add(
                Violation(
                    id=ident,
                    candidate_id=c_id,
                    plate=vehicle["plate_number"] if vehicle else None,
                    rule=raw["violation_type"],
                    location=raw["location"],
                    created_at=iso(raw.get("date_time")),
                )
            )
        db.flush()
        for source, raw in memo_rows:
            ident = str(raw["fine_id"])
            violation_id = str(raw["violation_id"])
            if not db.get(Violation, violation_id):
                raise ValueError(
                    "Legacy memo has an orphaned violation; repair a copy of the legacy database before importing"
                )
            existing = db.scalar(select(Memo).where(Memo.violation_id == violation_id))
            if existing:
                # Preserve conflicting fine/memo source data in the audit without creating a second issued memo.
                db.add(
                    Audit(
                        actor="migration",
                        action="LEGACY_MEMO_DUPLICATE_PRESERVED",
                        target=ident,
                        details={"source": source, "record": safe_json(raw)},
                    )
                )
                continue
            if db.get(Memo, ident):
                ident = f"{source}-{ident}"
            status = raw.get("status") or "UNPAID"
            if status == "PAID":
                status = "LEGACY_UNVERIFIED"
            db.add(
                Memo(
                    id=ident,
                    violation_id=violation_id,
                    fine_amount=raw["fine_amount"],
                    status=status,
                    policy_version="legacy-unknown",
                    payment_date=(
                        iso(raw["payment_date"]) if raw.get("payment_date") else None
                    ),
                )
            )
            db.add(
                Audit(
                    actor="migration",
                    action="IMPORT_LEGACY_MEMO",
                    target=ident,
                    details={"source": source, "record": safe_json(raw)},
                )
            )
        db.add(
            Setting(
                id="legacy_import_v1",
                value={
                    "completed_at": now(),
                    "users": len(users),
                    "violations": len(violations),
                    "memos": len(memo_rows),
                },
            )
        )
        db.add(
            Audit(
                actor="migration",
                action="IMPORT_LEGACY",
                target="v1",
                details={
                    "ownership": "pending reverification",
                    "old_paid": "unverified; not counted as collected revenue",
                },
            )
        )
    return {
        "users": len(users),
        "violations": len(violations),
        "memo_sources": len(memo_rows),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=["init", "provision", "recover", "import-legacy", "retention"],
    )
    parser.add_argument("--email")
    parser.add_argument(
        "--role", choices=["USER", "RTO", "GOVT", "ADMIN"], default="ADMIN"
    )
    parser.add_argument("--name", default="Project administrator")
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()
    app = create_app()
    engine = app.extensions["engine"]
    initialize(engine)
    if args.command == "init":
        print("Schema initialized; no demo accounts or remote database changes made.")
        return
    if args.command == "import-legacy":
        print(import_legacy(engine))
        return
    if args.command in ("provision", "recover"):
        if not args.email:
            parser.error("--email required")
        password = getpass.getpass("Set a unique password (10+ characters): ")
        if len(password) < 10:
            raise ValueError("Password must contain at least 10 characters")
        with transaction(engine) as db:
            user = db.scalar(
                select(User).where(User.email == args.email.strip().lower())
            )
            if args.command == "recover" and not user:
                raise ValueError("User not found")
            if not user:
                user = User(
                    email=args.email.strip().lower(),
                    full_name=args.name,
                    role=args.role,
                )
                db.add(user)
            user.password_hash = generate_password_hash(password)
            user.active = 1
            user.token_version = (user.token_version or 0) + 1
            if args.command == "provision":
                user.role = args.role
            db.flush()
            db.add(
                Audit(
                    actor="trusted-local-cli",
                    action=args.command.upper(),
                    target=user.id,
                    details={
                        "role": user.role,
                        "identity_check": "Administrator responsible for account recovery verification",
                    },
                )
            )
        print("Account saved. Password was not logged.")
        return
    if args.command == "retention":
        from datetime import datetime, timedelta, timezone

        if args.days < 1:
            raise ValueError("Retention must be at least 1 day")
        cutoff = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()
        keys = []
        with transaction(engine) as db:
            for c in db.scalars(select(Candidate).where(Candidate.created_at < cutoff)):
                keys.extend(e["key"] for e in c.evidence)
                c.observations = {
                    **c.observations,
                    "evidence_status": "Expired under retention policy",
                }
                c.evidence = []
            from .models import Dispute

            for d in db.scalars(select(Dispute).where(Dispute.created_at < cutoff)):
                keys.extend(e["key"] for e in d.evidence)
                d.evidence = []
            for j in db.scalars(
                select(Job).where(
                    Job.created_at < cutoff,
                    Job.status.in_(
                        [
                            "COMPLETED",
                            "FAILED",
                            "CANCELLED",
                            "AWAITING_UPLOAD",
                            "UPLOADED",
                        ]
                    ),
                )
            ):
                if j.object_key:
                    keys.append(j.object_key)
                    j.object_key = None
            for s in db.scalars(
                select(VideoSession).where(
                    VideoSession.created_at < cutoff, VideoSession.status != "RUNNING"
                )
            ):
                if s.preview_key:
                    keys.append(s.preview_key)
                    s.preview_key = None
                s.state = {}
            db.add(
                Audit(
                    actor="trusted-local-cli",
                    action="RETENTION",
                    target=cutoff,
                    details={"objects": len(keys)},
                )
            )
        for key in keys:
            app.extensions["storage"].delete(key)
        print(f"Expired {len(keys)} objects; audit and memo records retained.")


if __name__ == "__main__":
    main()
