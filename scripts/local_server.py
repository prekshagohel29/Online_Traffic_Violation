"""One local process for the React build, API and durable worker; preserves accounts."""

import argparse, secrets, threading, time, socket, os
from pathlib import Path
from flask import Flask, send_from_directory, abort
from waitress import serve
from backend.app import create_app, ROOT
from backend.db import initialize
from backend.worker import Worker


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=str(ROOT / "data"))
    parser.add_argument("--web-port", type=int, default=3001)
    args = parser.parse_args()
    data = Path(args.data_dir).resolve()
    data.mkdir(parents=True, exist_ok=True)
    for port in (5000, args.web_port):
        check = socket.socket()
        try:
            check.bind(("127.0.0.1", port))
        except OSError:
            raise SystemExit(
                f"Port {port} is already in use. The project may already be running; open http://127.0.0.1:{args.web_port}."
            )
        finally:
            check.close()
    keyfile = data / "secret"
    secret = keyfile.read_text() if keyfile.exists() else secrets.token_urlsafe(48)
    keyfile.write_text(secret)
    app = create_app(
        {
            "APP_ENV": "local",
            "DATA_DIR": str(data),
            "DATABASE_URL": "",
            "STORAGE_MODE": "local",
            "NOTIFICATION_MODE": "preview",
            "JWT_SECRET_KEY": secret,
            "FRONTEND_URL": f"http://127.0.0.1:{args.web_port}",
            "CORS_ORIGINS": [
                f"http://127.0.0.1:{args.web_port}",
                f"http://localhost:{args.web_port}",
                "http://localhost:3000",
            ],
        }
    )
    initialize(app.extensions["engine"])
    worker = Worker(app)

    def loop():
        while True:
            try:
                if not worker.tick():
                    time.sleep(0.3)
            except Exception as exc:
                print("Worker retrying after", type(exc).__name__, flush=True)
                time.sleep(2)

    threading.Thread(target=loop, daemon=True).start()
    threading.Thread(
        target=lambda: serve(app, host="127.0.0.1", port=5000, threads=6), daemon=True
    ).start()
    frontend = Flask("e-memo-local", static_folder=None)
    build = ROOT / "frontend/build"

    @frontend.get("/", defaults={"path": ""})
    @frontend.get("/<path:path>")
    def page(path):
        if (build / path).is_file():
            return send_from_directory(build, path)
        if "." in Path(path).name:
            abort(404)
        return send_from_directory(build, "index.html")

    @frontend.after_request
    def cache(response):
        if response.mimetype == "text/html":
            response.headers["Cache-Control"] = "no-store"
        return response

    print(f"e-Memo ready at http://127.0.0.1:{args.web_port}", flush=True)
    print(
        "Accounts and records persist in "
        + str(data)
        + ". Keep this terminal running.",
        flush=True,
    )
    serve(frontend, host="127.0.0.1", port=args.web_port, threads=4)


if __name__ == "__main__":
    main()
