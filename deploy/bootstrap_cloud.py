"""Explicitly initialize ONLY the new, empty Supabase deployment database.

Run this trusted CLI after Vercel linking and environment provisioning. It never
runs during web/worker startup and refuses an unknown target or populated DB.
"""

import argparse, hashlib, json, os, re, subprocess, sys
from pathlib import Path
from urllib.parse import urlparse
from dotenv import dotenv_values
from sqlalchemy import func, select, text
from backend.models import Base, User, Setting
from backend.db import make_engine, initialize
from backend.storage import Storage

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "prj_HPD7jRRYqtXl9EnASAwyQIeaDS23"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--expected-project-ref", required=True)
    args = parser.parse_args()
    linked = json.loads((ROOT / ".vercel/project.json").read_text())
    if linked["projectId"] != PROJECT:
        raise SystemExit("Unexpected Vercel project; nothing changed.")
    ref = args.expected_project_ref
    if not re.fullmatch(r"[a-z0-9]{15,30}", ref):
        raise SystemExit("Invalid Supabase project reference")
    values = {k: v for k, v in dotenv_values(args.env_file).items() if v is not None}
    needed = [
        "DATABASE_URL",
        "JWT_SECRET_KEY",
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "FRONTEND_URL",
        "CORS_ORIGINS",
    ]
    if any(not values.get(k) for k in needed):
        raise SystemExit("Missing deployment environment values")
    if (
        urlparse(values["SUPABASE_URL"]).hostname != ref + ".supabase.co"
        or ref not in values["DATABASE_URL"]
    ):
        raise SystemExit(
            "Database/storage do not match the NEW provisioned project. Nothing changed."
        )
    values.update(
        APP_ENV="production",
        STORAGE_MODE="supabase",
        STORAGE_BUCKET="traffic-private",
        DATA_DIR=str(ROOT / "data/cloud-tmp"),
    )
    os.environ.update(values)
    destination = make_engine(values["DATABASE_URL"])
    with destination.connect() as conn:
        exists = conn.scalar(text("SELECT to_regclass('public.tv_users')"))
        if exists and conn.scalar(select(func.count()).select_from(User)):
            raise SystemExit(
                "Cloud database already has users; initialization refused to preserve existing records."
            )
    # Reuse the existing explicit fictional fixture generator in a NEW local DB.
    local = ROOT / "data/cloud-bootstrap"
    env = os.environ.copy()
    env.update(APP_ENV="local", DATABASE_URL="", STORAGE_MODE="local")
    subprocess.run(
        [sys.executable, "-m", "scripts.seed_showcase", "--data-dir", str(local)],
        cwd=ROOT,
        env=env,
        check=True,
    )
    source = make_engine("sqlite:///" + (local / "traffic.db").as_posix())
    # Migrations target only the just-provisioned database. No old DB is opened.
    raw = destination.raw_connection()
    try:
        raw.driver_connection.autocommit = True
        with raw.cursor() as cursor:
            for name in [
                "001_schema.sql",
                "002_private_access.sql",
                "003_supabase_storage.sql",
                "004_casebook.sql",
            ]:
                cursor.execute((ROOT / "migrations" / name).read_text(), prepare=False)
    finally:
        raw.close()
    initialize(destination)
    cloud = Storage(values)
    uploaded = 0
    for path in sorted((local / "objects").rglob("*")):
        if path.is_file():
            key = path.relative_to(local / "objects").as_posix()
            cloud.put(key, path.read_bytes(), "image/jpeg")
            uploaded += 1
    counts = {}
    # PostgreSQL core inserts retain the published schema's JSON/foreign-key types.
    with source.connect() as src, destination.begin() as dst:
        for table in Base.metadata.sorted_tables:
            rows = [dict(row) for row in src.execute(select(table)).mappings()]
            if rows:
                dst.execute(table.insert(), rows)
            counts[table.name] = len(rows)
        dst.execute(
            Setting.__table__.insert(),
            {
                "id": "cloud-demo-bootstrap",
                "value": {
                    "vercel_project": PROJECT,
                    "supabase_project": ref,
                    "fictional_data": True,
                },
            },
        )
    private = ROOT / ".vercel/private"
    private.mkdir(parents=True, exist_ok=True)
    access = json.loads((local / "test-access.json").read_text())
    lines = [
        "# Private cloud demonstration accounts",
        "",
        "These accounts belong only to the new online-traffic-violation database.",
        "",
        "| Role | Email | Password |",
        "|---|---|---|",
    ]
    for role, item in access.items():
        lines.append(f"| {role} | {item['email']} | `{item['password']}` |")
    (private / "CLOUD_DEMO_ACCOUNTS.md").write_text("\n".join(lines) + "\n")
    (private / "cloud-bootstrap-result.json").write_text(
        json.dumps(
            {"supabase_project": ref, "tables": counts, "private_objects": uploaded},
            indent=2,
        )
    )
    source.dispose()
    destination.dispose()
    print(
        "Initialized the new isolated cloud database with fictional examples and private evidence."
    )
    print("Private login details saved locally; no passwords printed or committed.")


if __name__ == "__main__":
    main()
