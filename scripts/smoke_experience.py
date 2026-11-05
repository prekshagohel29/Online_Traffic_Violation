import json, secrets
from pathlib import Path
from backend.app import create_app, ROOT
from backend.db import initialize


def main():
    data = ROOT / "data/browser-qa"
    access = json.loads((data / "test-access.json").read_text())
    app = create_app(
        {
            "JWT_SECRET_KEY": (data / "secret").read_text(),
            "DATA_DIR": str(data),
            "DATABASE_URL": "",
            "STORAGE_MODE": "local",
            "APP_ENV": "local",
        }
    )
    initialize(app.extensions["engine"])
    client = app.test_client()
    for role in ["RTO", "GOVT", "USER", "OTHER", "ADMIN"]:
        r = client.post("/api/auth/login", json=access[role])
        assert r.status_code == 200, r.json
        h = {"Authorization": "Bearer " + r.json["access_token"]}
        summary = client.get("/api/overview", headers=h)
        assert summary.status_code == 200, summary.json
        cases = client.get("/api/cases?size=100", headers=h)
        assert cases.status_code == 200, cases.json
        print(role, "overview/cases", summary.json["total"], len(cases.json["items"]))
        if role == "GOVT":
            for case in cases.json["items"]:
                assert case["vehicle"] is None and case["plate"] is None
                d = client.get("/api/cases/" + case["id"], headers=h)
                assert d.status_code == 200
                assert not d.json["evidence"]
                assert not d.json["observations"]
        if role == "RTO":
            assets = client.get("/api/datasets", headers=h)
            assert assets.status_code == 200
            print("Dataset assets", len(assets.json["items"]))
            registry = client.get("/api/registry", headers=h)
            assert registry.status_code == 200, registry.json
            print("Vehicle profiles", registry.json["total"])
    print("Role workflows and government privacy checks passed.")


if __name__ == "__main__":
    main()
