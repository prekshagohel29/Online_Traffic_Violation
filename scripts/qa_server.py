"""Isolated local QA harness. Random credentials; never remote data or real notices."""

import secrets, json, threading, time, mimetypes, argparse, socket
from pathlib import Path
from flask import Flask, send_from_directory, abort
from waitress import serve
from werkzeug.security import generate_password_hash
from sqlalchemy import select
from backend.app import create_app, ROOT
from backend.models import User, Camera
from backend.db import initialize, transaction
from backend.rules import validate_config
from backend.worker import Worker


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--web-port", type=int, default=3001)
    parser.add_argument("--api-port", type=int, default=5000)
    args = parser.parse_args()
    for port in (args.web_port, args.api_port):
        check = socket.socket()
        try:
            check.bind(("127.0.0.1", port))
        except OSError:
            raise SystemExit(
                f"QA port {port} is already in use; choose separate test ports."
            )
        finally:
            check.close()
    data = ROOT / "data" / "browser-qa"
    data.mkdir(parents=True, exist_ok=True)
    secretfile = data / "secret"
    secret = (
        secretfile.read_text() if secretfile.exists() else secrets.token_urlsafe(48)
    )
    secretfile.write_text(secret)
    app = create_app(
        {
            "DATA_DIR": str(data),
            "DATABASE_URL": "",
            "JWT_SECRET_KEY": secret,
            "APP_ENV": "local",
            "STORAGE_MODE": "local",
            "NOTIFICATION_MODE": "preview",
            "FRONTEND_URL": f"http://127.0.0.1:{args.web_port}",
            "CORS_ORIGINS": [
                f"http://127.0.0.1:{args.web_port}",
                f"http://localhost:{args.web_port}",
            ],
        }
    )
    initialize(app.extensions["engine"])
    access = {}
    with transaction(app.extensions["engine"]) as db:
        for role in ("RTO", "ADMIN", "USER", "GOVT"):
            email = "qa-" + role.lower() + "@example.test"
            password = secrets.token_urlsafe(18)
            u = db.scalar(select(User).where(User.email == email))
            if not u:
                u = User(email=email, full_name="QA " + role, role=role)
                db.add(u)
            u.password_hash = generate_password_hash(password)
            access[role] = {"email": email, "password": password}
        if not db.scalar(
            select(Camera.id).where(Camera.name == "CC0 rush-hour sample")
        ):
            db.add(
                Camera(
                    name="CC0 rush-hour sample",
                    location="Prerecorded sample — experimental zone",
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
    (data / "access.json").write_text(json.dumps(access), encoding="utf-8")
    worker = Worker(app)

    def work():
        while True:
            try:
                if not worker.tick():
                    time.sleep(0.25)
            except Exception as exc:
                print("QA worker retry:", type(exc).__name__, flush=True)
                time.sleep(2)

    threading.Thread(target=work, daemon=True).start()
    frontend = Flask("react-preview", static_folder=None)
    build = ROOT / "frontend" / "build"

    @frontend.get("/", defaults={"path": ""})
    @frontend.get("/<path:path>")
    def spa(path):
        if (build / path).is_file():
            return send_from_directory(build, path)
        if "." in Path(path).name:
            abort(404)
        return send_from_directory(build, "index.html")

    threading.Thread(
        target=lambda: serve(app, host="127.0.0.1", port=args.api_port, threads=6),
        daemon=True,
    ).start()
    print(
        f"Isolated QA: React http://127.0.0.1:{args.web_port}; API http://127.0.0.1:{args.api_port}",
        flush=True,
    )
    serve(frontend, host="127.0.0.1", port=args.web_port, threads=4)


if __name__ == "__main__":
    main()
