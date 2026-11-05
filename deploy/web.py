"""Serve the existing React build and authenticated API from one cloud origin."""

import os
from pathlib import Path
from flask import abort, send_from_directory
from backend.app import ROOT, create_app
from backend.db import initialize


def cloud_app(overrides=None, build_dir=None):
    # Vercel system variables let a newly generated deployment use its own HTTPS
    # origin. Explicit settings always take precedence for the canonical domain.
    host = os.getenv("VERCEL_PROJECT_PRODUCTION_URL") or os.getenv("VERCEL_URL")
    if host:
        origin = "https://" + host.removeprefix("https://").rstrip("/")
        os.environ.setdefault("FRONTEND_URL", origin)
        os.environ.setdefault("CORS_ORIGINS", origin)
    app = create_app(overrides)
    build = Path(build_dir or ROOT / "frontend/build").resolve()

    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def react_page(path):
        # Unknown API routes must retain an API error, never the SPA's HTML.
        if path == "api" or path.startswith("api/"):
            abort(404)
        candidate = (build / path).resolve()
        if not candidate.is_relative_to(build):
            abort(404)
        if candidate.is_file():
            return send_from_directory(build, path)
        if "." in Path(path).name:
            abort(404)
        if not (build / "index.html").is_file():
            abort(503, description="React build unavailable")
        return send_from_directory(build, "index.html")

    return app


def main():
    from waitress import serve

    app = cloud_app()
    initialize(app.extensions["engine"])
    serve(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8080")),
        threads=6,
        max_request_body_size=app.config["MAX_UPLOAD_BYTES"],
    )


if __name__ == "__main__":
    main()
