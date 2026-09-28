"""Nadun assignment 2: privacy and data leakage assessment cases."""
from __future__ import annotations

import json
from pathlib import Path

from backend import api, config, db, security
from tests.conftest import login, register


def test_tc01_employee_a_cannot_read_employee_b_records(client, agent_http):
    headers_a = login(client)
    run_id = client.post("/api/runs", headers=headers_a).json()["id"]
    notice_id = client.get("/api/notifications").json()[0]["id"]
    _, headers_b = register(client, "other-user@example.com")
    assert client.get(f"/api/runs/{run_id}").status_code == 404
    assert client.post(f"/api/notifications/{notice_id}/read", headers=headers_b).status_code == 404


def test_tc02_employee_attempts_hr_aggregate_api(client):
    login(client)
    response = client.get("/api/admin/overview")
    assert response.status_code == 403
    assert "employee_count" not in response.text


def test_tc03_employee_attempts_admin_ingestion(client):
    headers = login(client)
    course = client.get("/api/courses").json()[0]
    payload = {key: value for key, value in course.items() if key in config.CourseInput.model_fields}
    response = client.post("/api/admin/courses", json=payload, headers=headers)
    assert response.status_code == 403


def test_tc04_anonymous_private_endpoints_return_no_personal_data(client):
    for endpoint in ["/api/profile", "/api/recommendations", "/api/notifications", "/api/privacy/export"]:
        response = client.get(endpoint)
        assert response.status_code == 401


def test_tc05_session_reuse_after_logout_is_rejected(client):
    headers = login(client)
    token = client.cookies.get(api.COOKIE)
    assert token
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert db.session_get(security.digest_token(token)) is None
    assert client.get("/api/profile").status_code == 401


def test_tc06_session_reuse_after_account_deletion_is_rejected(client):
    _, headers = register(client, "delete-me@example.com")
    token = client.cookies.get(api.COOKIE)
    assert client.request("DELETE", "/api/privacy/account", json={"password": "StrongPass123!"}, headers=headers).status_code == 200
    assert db.session_get(security.digest_token(token)) is None
    assert client.get("/api/profile").status_code == 401


def test_tc07_csrf_is_required_for_profile_edit(client):
    login(client)
    profile = client.get("/api/profile").json()
    response = client.put("/api/profile", json={**profile, "career_goal": "AI Engineer"})
    assert response.status_code == 403
    assert client.get("/api/profile").json()["career_goal"] != "AI Engineer"


def test_tc08_privacy_export_excludes_secrets_and_other_users(client):
    user, _ = register(client, "export-me@example.com")
    db.save_run(user["user"]["id"], {"id": "r1", "status": "completed", "started_at": config.utcnow(), "steps": []})
    register(client, "other-export@example.com")
    response = client.post("/api/auth/login", json={"email": "export-me@example.com", "password": "StrongPass123!"})
    assert response.status_code == 200
    exported = client.get("/api/privacy/export").text
    assert "password_hash" not in exported
    assert "csrf_token" not in exported
    assert "other-export@example.com" not in exported
    assert "export-me@example.com" in exported


def test_tc09_consent_off_blocks_discovery_and_chat(client):
    _, headers = register(client, "consent-off@example.com")
    assert client.post("/api/runs", headers=headers).status_code == 403
    assert client.post("/api/chat", json={"message": "What next?"}, headers=headers).status_code == 403


def test_tc10_consent_revoked_during_run_prevents_stale_commit(client, monkeypatch):
    headers = login(client)

    async def changed(kind, port, run_id, user_id, payload):
        profile = db.profile(db.user_by_id(user_id))
        db.save_profile(user_id, {**profile, "consent": False})
        return {"current_skills": [], "target_skills": [], "skill_gaps": [], "priority_skills": []}

    monkeypatch.setattr(api, "call_agent", changed)
    run = client.post("/api/runs", headers=headers).json()
    assert run["status"] == "failed"
    assert "consent was withdrawn" in run["error"]
    assert client.get("/api/recommendations").json() == []


def test_tc11_passwords_and_sessions_are_hashed_at_rest(client):
    user, _ = register(client, "hash-check@example.com")
    private = db.user_by_id(user["user"]["id"])
    assert "StrongPass123!" not in private["password_hash"]
    assert security.verify_password("StrongPass123!", private["password_hash"])
    token = client.cookies.get(api.COOKIE)
    with db.connection() as conn:
        row = conn.execute("SELECT token_hash FROM sessions WHERE user_id=?", (user["user"]["id"],)).fetchone()
    assert row["token_hash"] == security.digest_token(token)
    assert row["token_hash"] != token


def test_tc12_plaintext_sqlite_limitation_is_documented_and_file_is_owner_only(client):
    path = Path(config.db_path())
    assert path.exists()
    assert path.read_bytes().startswith(b"SQLite format 3")
    assert oct(path.stat().st_mode & 0o777) == "0o600"


def test_tc13_validation_errors_do_not_echo_passwords(client):
    response = client.post("/api/auth/register", json={"name": "A", "email": "bad", "password": "SuperSecret123!"})
    assert response.status_code == 422
    assert "SuperSecret123!" not in response.text


def test_tc14_login_rate_limit_reduces_brute_force_leakage(client):
    for index in range(8):
        response = client.post("/api/auth/login", json={"email": "alex@skillscout.demo", "password": "wrong"}, headers={"X-Forwarded-For": str(index)})
        assert response.status_code == 401
    assert client.post("/api/auth/login", json={"email": "alex@skillscout.demo", "password": "wrong"}).status_code == 429


def test_tc15_account_deletion_removes_application_records(client):
    user, headers = register(client, "delete-records@example.com")
    uid = user["user"]["id"]
    db.save_run(uid, {"id": "r1", "status": "completed", "started_at": config.utcnow(), "steps": []})
    with db.connection() as conn:
        conn.execute("INSERT INTO analyses VALUES (?,?,?)", (uid, 1, json.dumps({"needs": {}, "trends": [], "recommendations": []})))
    assert client.request("DELETE", "/api/privacy/account", json={"password": "StrongPass123!"}, headers=headers).status_code == 200
    assert db.user_by_id(uid) is None
    assert db.runs(uid, None) == []
    assert db.analysis(uid) == {"needs": None, "trends": [], "recommendations": []}
