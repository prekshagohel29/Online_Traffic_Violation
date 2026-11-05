"""Check cloud SPA routing without weakening the existing API access controls."""

from deploy.web import cloud_app


def test_cloud_spa_and_private_api(tmp_path):
    build = tmp_path / "build"
    build.mkdir()
    (build / "index.html").write_text("<html>React shell</html>")
    (build / "static").mkdir()
    (build / "static/app.js").write_text('console.log("bundled");')
    app = cloud_app(
        {
            "TESTING": True,
            "APP_ENV": "local",
            "DATABASE_URL": "",
            "DATA_DIR": str(tmp_path / "data"),
            "STORAGE_MODE": "local",
            "JWT_SECRET_KEY": "isolated-cloud-routing-test-secret-at-least-32-characters",
        },
        build,
    )
    client = app.test_client()
    try:
        assert client.get("/").status_code == 200
        assert b"React shell" in client.get("/government").data
        assert b"React shell" in client.get("/cases/demo-case").data
        assert client.get("/static/app.js").status_code == 200
        assert client.get("/static/missing.js").status_code == 404
        unknown = client.get("/api/not-a-real-route")
        assert unknown.status_code == 404 and unknown.is_json
        private = client.get("/api/admin/users")
        assert private.status_code == 401 and private.is_json
    finally:
        app.extensions["engine"].dispose()
