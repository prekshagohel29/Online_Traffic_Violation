def test_cloud_demo_requires_explicit_opt_in_and_staff_role(app, client, accounts):
    app.config.update(APP_ENV="production", ENABLE_DEMO_FEATURES=False)
    staff = accounts["RTO"]["headers"]
    citizen = accounts["USER"]["headers"]
    assert client.get("/api/datasets", headers=staff).json["demo_enabled"] is False
    assert (
        client.post("/api/samples/rush-hour/run", json={}, headers=staff).status_code
        == 403
    )
    app.config["ENABLE_DEMO_FEATURES"] = True
    assert client.get("/api/datasets", headers=staff).json["demo_enabled"] is True
    assert (
        client.post("/api/samples/rush-hour/run", json={}, headers=citizen).status_code
        == 403
    )
    response = client.post("/api/samples/rush-hour/run", json={}, headers=staff)
    assert response.status_code == 503 and "worker" in response.json["msg"]
