from sqlalchemy import text, select, func
from backend.db import transaction
from backend.manage import import_legacy
from backend.models import User, Link, Memo, Violation


def test_upgrade_preserves_records_and_reclassifies_unverified(app):
    engine = app.extensions["engine"]
    with engine.begin() as c:
        for sql in [
            "CREATE TABLE users (user_id TEXT PRIMARY KEY,email TEXT,password_hash TEXT,role TEXT,full_name TEXT)",
            "CREATE TABLE vehicle (vehicle_id INTEGER PRIMARY KEY,plate_number TEXT)",
            "CREATE TABLE user_vehicles (user_id TEXT,vehicle_id INTEGER)",
            "CREATE TABLE violation (violation_id INTEGER PRIMARY KEY,vehicle_id INTEGER,violation_type TEXT,location TEXT,date_time TEXT)",
            "CREATE TABLE memo (fine_id INTEGER PRIMARY KEY,violation_id INTEGER,fine_amount INTEGER,status TEXT)",
            "INSERT INTO users VALUES ('original-user-id','legacy@test.dev','original-password-hash','USER','Legacy user')",
            "INSERT INTO users VALUES ('default-admin','admin@system.com','old-default-hash','ADMIN','Old demo')",
            "INSERT INTO vehicle VALUES (41,'GJ01AB1234')",
            "INSERT INTO user_vehicles VALUES ('original-user-id',41)",
            "INSERT INTO violation VALUES (72,41,'Signal Jump','Legacy junction','2026-01-01T00:00:00+00:00')",
            "INSERT INTO memo VALUES (83,72,500,'PAID')",
        ]:
            c.execute(text(sql))
    summary = import_legacy(engine)
    assert summary["violations"] == 1
    assert import_legacy(engine)["already_imported"] is True
    with transaction(engine) as db:
        assert (
            db.get(User, "original-user-id").password_hash == "original-password-hash"
        )
        assert db.get(User, "default-admin").active == 0
        assert db.scalar(select(Link)).status == "PENDING"
        assert db.get(Violation, "72").plate == "GJ01AB1234"
        assert db.get(Memo, "83").status == "LEGACY_UNVERIFIED"
        assert db.scalar(select(func.count()).select_from(Memo)) == 1
    with engine.connect() as c:
        assert c.scalar(text("SELECT fine_amount FROM memo WHERE fine_id=83")) == 500


def test_upgrade_from_fine_without_auth_tables(app):
    engine = app.extensions["engine"]
    with engine.begin() as c:
        c.execute(
            text(
                "CREATE TABLE vehicle(vehicle_id INTEGER PRIMARY KEY,plate_number TEXT)"
            )
        )
        c.execute(
            text(
                "CREATE TABLE violation(violation_id INTEGER PRIMARY KEY,vehicle_id INTEGER,violation_type TEXT,location TEXT)"
            )
        )
        c.execute(
            text(
                "CREATE TABLE fine(fine_id INTEGER PRIMARY KEY,violation_id INTEGER,fine_amount INTEGER)"
            )
        )
        c.execute(text("INSERT INTO vehicle VALUES (1,'22BH1234AA')"))
        c.execute(text("INSERT INTO violation VALUES (2,1,'Speeding','Test')"))
        c.execute(text("INSERT INTO fine VALUES (3,2,1000)"))
    import_legacy(engine)
    with transaction(engine) as db:
        assert db.get(Memo, "3").fine_amount == 1000
