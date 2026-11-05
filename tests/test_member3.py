"""Member 3 regression checks using the shared authenticated app fixtures."""

from sqlalchemy import select
from backend.db import transaction
from backend.models import Candidate, CaseMetadata, Violation, Memo, Link, User, Audit


def records(app, accounts):
    with transaction(app.extensions["engine"]) as db:
        db.add(
            Link(user_id=accounts["USER"]["id"], plate="GJ00DM3001", status="APPROVED")
        )
        for ident, location, kind in [
            ("m3-demo", "Demo Ahmedabad", True),
            ("m3-recorded", "Demo Vadodara", False),
        ]:
            db.add(
                Candidate(
                    id=ident,
                    event_key=ident,
                    rule="restricted_zone",
                    plate="GJ00DM3001",
                    location=location,
                    status="CONFIRMED",
                    created_at="2026-11-04T20:00:00+00:00",
                    explanation="Private owner identifying observation",
                    observations={"private": "owner-data"},
                    raw_ocr=[{"raw": "GJ00DM3001"}],
                    reviewer=accounts["RTO"]["id"],
                    evidence=[
                        {"key": "private/example.jpg", "sha256": "private-fixture"}
                    ],
                )
            )
            db.flush()
            db.add(CaseMetadata(id=ident, is_demo=int(kind)))
            db.add(
                Violation(
                    id="v-" + ident,
                    candidate_id=ident,
                    plate="GJ00DM3001",
                    rule="restricted_zone",
                    location=location,
                )
            )
            db.flush()
            db.add(
                Memo(
                    id="memo-" + ident,
                    violation_id="v-" + ident,
                    fine_amount=500,
                    status="UNPAID" if kind else "SANDBOX_PAID",
                )
            )


def test_member3_reporting_filters_and_ist_days(app, client, accounts):
    records(app, accounts)
    h = accounts["GOVT"]["headers"]
    data = client.get(
        "/api/overview?scope=demo&type=restricted_zone&location=Demo%20Ahmedabad",
        headers=h,
    ).json
    assert (
        data["total"] == 1 and data["confirmed"] == 1 and data["money"]["UNPAID"] == 500
    )
    assert data["trend"] == [{"date": "2026-11-05", "cases": 1}]
    choices = client.get("/api/case-filters", headers=h).json
    assert choices["locations"] == ["Demo Ahmedabad", "Demo Vadodara"]
    assert client.get("/api/overview?from=invalid", headers=h).status_code == 400


def test_member3_government_redaction_and_citizen_scoping(app, client, accounts):
    records(app, accounts)
    case = client.get("/api/cases/m3-demo", headers=accounts["GOVT"]["headers"]).json
    assert case["plate"] is case["vehicle"] is case["reviewer"] is None
    assert case["evidence"] == [] and case["ocr"] == [] and case["observations"] == {}
    assert "Private owner" not in str(case)
    assert (
        client.get("/api/cases", headers=accounts["OTHER"]["headers"]).json["total"]
        == 0
    )
    assert (
        client.get(
            "/api/cases/m3-demo", headers=accounts["OTHER"]["headers"]
        ).status_code
        == 404
    )


def test_member3_role_provisioning_revokes_old_session(app, client, accounts):
    h = accounts["ADMIN"]["headers"]
    ident = accounts["USER"]["id"]
    assert (
        client.patch(
            "/api/admin/users/" + ident,
            json={"role": "RTO", "reason": "Documented trusted staff assignment"},
            headers=h,
        ).status_code
        == 200
    )
    assert (
        client.get("/api/auth/me", headers=accounts["USER"]["headers"]).status_code
        == 401
    )
    assert (
        client.patch(
            "/api/admin/users/" + accounts["ADMIN"]["id"],
            json={"role": "USER", "reason": "Self downgrade"},
            headers=h,
        ).status_code
        == 409
    )
    assert (
        client.get("/api/admin/users", headers=accounts["GOVT"]["headers"]).status_code
        == 403
    )


def test_member3_policy_version_and_audit(app, client, accounts):
    h = accounts["ADMIN"]["headers"]
    policy = client.get("/api/admin/policy", headers=h).json
    bases = dict(policy["bases"])
    bases["restricted_zone"] += 1
    response = client.put("/api/admin/policy", json={"bases": bases}, headers=h)
    assert response.status_code == 200 and response.json["version"] != policy["version"]
    assert client.get("/api/admin/policy", headers=h).json["bases"] == bases
    assert (
        client.get("/api/admin/audit", headers=h).json["items"][0]["action"]
        == "UPDATE_DEMO_POLICY"
    )
    assert (
        client.put("/api/admin/policy", json={"bases": {}}, headers=h).status_code
        == 400
    )
    assert (
        client.get("/api/admin/policy", headers=accounts["RTO"]["headers"]).status_code
        == 403
    )


def test_member3_legacy_analytics_and_service_summary(app, client, accounts):
    records(app, accounts)
    result = client.get("/api/gov/analytics", headers=accounts["GOVT"]["headers"])
    assert result.status_code == 200 and result.json["kpi"]["total_violations"] == 2
    assert (
        result.json["kpi"]["total_revenue"] == 500
        and result.json["revenue_mode"] == "SANDBOX ONLY"
    )
    assert (
        client.get(
            "/api/operator/health", headers=accounts["ADMIN"]["headers"]
        ).status_code
        == 200
    )
    assert (
        client.get(
            "/api/operator/health", headers=accounts["GOVT"]["headers"]
        ).status_code
        == 403
    )
