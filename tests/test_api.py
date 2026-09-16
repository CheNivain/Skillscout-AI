"""API boundaries and real orchestration logic, without network/model dependencies."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend import api, config, db, security, worker
from backend.ai import engine


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SKILLSCOUT_DB_PATH", str(tmp_path / "workspace.db"))
    monkeypatch.setenv("SKILLSCOUT_SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("SKILLSCOUT_SEED_DEMO", "true")
    monkeypatch.setenv("SKILLSCOUT_AGENT_KEY", "test-agent-secret")
    monkeypatch.setattr(security, "limiter", security.RateLimiter())
    monkeypatch.setattr(engine, "_complete_llm", lambda *args, **kwargs: (None, None))
    monkeypatch.setattr(engine, "get_model_status", lambda: {"llm_available": False, "provider": "ollama", "model": "test", "description": "Offline test"})
    with TestClient(api.app) as session:
        yield session


def login(client, role="alex"):
    response = client.post("/api/auth/login", json={"email": f"{role}@skillscout.demo", "password": "SkillScout123!"})
    assert response.status_code == 200, response.text
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def register(client, email="learner@example.com"):
    response = client.post("/api/auth/register", json={"name": "New Learner", "email": email, "password": "StrongPass123!"})
    assert response.status_code == 200, response.text
    return response.json(), {"X-CSRF-Token": response.json()["csrf_token"]}


@pytest.fixture
def agent_http(monkeypatch):
    """Simulate the wire transport, still executing all four real agent algorithms."""
    called = []
    original_client = httpx.AsyncClient

    async def handler(request):
        envelope = json.loads(request.content)
        kind = dict((port, kind) for kind, _, port, _ in config.AGENTS)[request.url.port]
        assert request.headers["x-agent-key"] == "test-agent-secret"
        assert envelope["user_id"]
        called.append(kind)
        functions = {"profile": engine.analyze_profile, "trends": engine.discover_trends,
                     "retrieval": engine.retrieve_courses, "recommendations": engine.recommend}
        result = functions[kind](**envelope["payload"])
        return httpx.Response(200, json={"run_id": envelope["run_id"], "agent": kind, "result": result})

    monkeypatch.setattr(api.httpx, "AsyncClient", lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs))
    return called


def test_auth_cookie_session_rotation_and_logout_csrf(client):
    assert client.get("/api/profile").status_code == 401
    response = client.post("/api/auth/login", json={"email": " ALEX@SKILLSCOUT.DEMO ", "password": "SkillScout123!"})
    assert response.status_code == 200
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "samesite=lax" in response.headers["set-cookie"].lower()
    old_token = client.cookies.get(api.COOKIE)
    headers = login(client)
    assert client.cookies.get(api.COOKIE) != old_token
    assert db.session_get(security.digest_token(old_token)) is None
    assert client.post("/api/auth/logout").status_code == 403
    assert client.get("/api/auth/session").json()["csrf_token"] == headers["X-CSRF-Token"]
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/profile").status_code == 401


def test_csrf_origin_and_input_validation(client):
    headers = login(client)
    profile = client.get("/api/profile").json()
    assert client.put("/api/profile", json=profile).status_code == 403
    assert client.put("/api/profile", json=profile, headers={**headers, "Origin": "https://attacker.example"}).status_code == 403
    assert client.put("/api/profile", json=profile, headers={**headers, "Origin": "http://localhost:5173"}).status_code == 200
    assert client.put("/api/profile", json={**profile, "budget": -1}, headers=headers).status_code == 422
    assert client.put("/api/profile", json={**profile, "role": "admin"}, headers=headers).status_code == 422
    response = client.post("/api/auth/register", json={"name": "  ", "email": "bad", "password": "SECRET"})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)
    assert "SECRET" not in response.text
    assert client.post("/api/auth/login", json={"email": "alex@skillscout.demo", "password": "wrong"}, headers={"Origin": "https://attacker.example"}).status_code == 403


def test_register_employee_only_casefold_and_hash_storage(client):
    user, _ = register(client, "NewUser@Example.com")
    assert user["user"]["role"] == "employee"
    assert user["user"]["email"] == "newuser@example.com"
    assert not client.get("/api/profile").json()["consent"]
    private = db.user_by_id(user["user"]["id"])
    assert "StrongPass123!" not in private["password_hash"]
    assert security.verify_password("StrongPass123!", private["password_hash"])
    assert client.post("/api/auth/register", json={"name": "Someone", "email": "NEWUSER@EXAMPLE.COM", "password": "StrongPass123!"}).status_code == 409
    assert client.post("/api/auth/register", json={"name": "Someone", "email": "other@example.com", "password": "StrongPass123!", "role": "admin"}).status_code == 422


def test_rate_limit_cannot_be_bypassed_with_forwarded_header(client):
    for index in range(8):
        assert client.post("/api/auth/login", json={"email": "alex@skillscout.demo", "password": "wrong"}, headers={"X-Forwarded-For": str(index)}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "alex@skillscout.demo", "password": "wrong"}, headers={"X-Forwarded-For": "different"}).status_code == 429


def test_consent_applies_to_runs_and_chat(client, monkeypatch):
    _, headers = register(client)
    called = []
    monkeypatch.setattr(engine, "answer_question", lambda *args: called.append(args))
    assert client.post("/api/runs", headers=headers).status_code == 403
    assert client.post("/api/chat", json={"message": "What should I learn?"}, headers=headers).status_code == 403
    assert not called
    profile = client.get("/api/profile").json()
    assert client.put("/api/profile", json={**profile, "consent": True}, headers=headers).status_code == 200
    assert client.post("/api/runs", headers=headers).status_code == 400  # Incomplete career profile.


def test_full_http_pipeline_persists_recommendations_and_deduplicates_notices(client, agent_http):
    headers = login(client)
    first = client.post("/api/runs", headers=headers)
    assert first.status_code == 200, first.text
    run = first.json()
    assert run["status"] == "completed", run
    assert agent_http == ["profile", "trends", "retrieval", "recommendations"]
    assert all(step["status"] == "completed" for step in run["steps"])
    dashboard = client.get("/api/dashboard").json()
    assert "Python" in dashboard["needs"]["skill_gaps"]
    assert dashboard["recommendations"]
    before = client.get("/api/notifications").json()
    assert before
    assert client.post("/api/runs", headers=headers).json()["status"] == "completed"
    assert len(client.get("/api/notifications").json()) == len(before)
    assert client.get(f"/api/runs/{run['id']}").json()["status"] == "completed"
    assert len(client.get("/api/runs").json()) == 2


def test_failed_agent_is_recorded_without_committing_analysis(client, monkeypatch):
    headers = login(client)
    async def broken(*args, **kwargs):
        raise RuntimeError("The profile agent is unavailable")
    monkeypatch.setattr(api, "call_agent", broken)
    run = client.post("/api/runs", headers=headers).json()
    assert run["status"] == "failed"
    assert run["finished_at"]
    assert run["error"] == "The profile agent is unavailable"
    assert client.get("/api/recommendations").json() == []
    assert client.get("/api/runs").json()[0] == run
    assert not api.RUNNING_USERS


def test_pipeline_timeout_persists_failed_trace_and_releases_account(client, monkeypatch):
    headers = login(client)
    monkeypatch.setattr(api, "PIPELINE_TIMEOUT", 0.02)
    async def slow(*args, **kwargs):
        await asyncio.sleep(5)
    monkeypatch.setattr(api, "call_agent", slow)
    response = client.post("/api/runs", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "failed"
    assert "time limit" in response.json()["error"]
    assert client.get("/api/runs").json()[0]["status"] == "failed"
    assert not api.RUNNING_USERS


def test_profile_change_during_run_prevents_stale_commit(client, monkeypatch):
    headers = login(client)
    async def changed(kind, port, run_id, user_id, payload):
        profile = db.profile(db.user_by_id(user_id))
        db.save_profile(user_id, {**profile, "consent": False})
        return engine.analyze_profile(payload["profile"])
    monkeypatch.setattr(api, "call_agent", changed)
    run = client.post("/api/runs", headers=headers).json()
    assert run["status"] == "failed"
    assert "consent was withdrawn" in run["error"]
    assert client.get("/api/recommendations").json() == []
    assert client.get("/api/notifications").json() == []


def test_simultaneous_runs_are_rejected(client, monkeypatch):
    user = db.user_by_email("alex@skillscout.demo")
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()
        async def slow(_user):
            entered.set()
            await release.wait()
            return {"status": "completed"}
        monkeypatch.setattr(api, "_execute_pipeline", slow)
        first = asyncio.create_task(api.execute_pipeline(user))
        await entered.wait()
        with pytest.raises(HTTPException) as rejected:
            await api.execute_pipeline(user)
        assert rejected.value.status_code == 409
        release.set()
        assert (await first)["status"] == "completed"
    asyncio.run(scenario())
    assert not api.RUNNING_USERS


def test_user_data_access_is_scoped_and_profile_id_cannot_be_changed(client, agent_http):
    headers = login(client)
    run = client.post("/api/runs", headers=headers).json()
    notification = client.get("/api/notifications").json()[0]
    owner_id = client.get("/api/auth/session").json()["user"]["id"]
    second, second_headers = register(client)
    assert client.get(f"/api/runs/{run['id']}").status_code == 404
    assert client.post(f"/api/notifications/{notification['id']}/read", headers=second_headers).status_code == 404
    assert client.get("/api/recommendations").json() == []
    assert client.get("/api/learning-plan").json() == []
    profile = client.get("/api/profile").json()
    response = client.put("/api/profile", json={**profile, "user_id": owner_id}, headers=second_headers)
    assert response.json()["user_id"] == second["user"]["id"]
    assert db.profile(db.user_by_id(owner_id))["role_title"] == "Data Analyst"


def test_completed_training_updates_skills_once_and_invalidates_analysis(client, agent_http):
    headers = login(client)
    assert client.post("/api/runs", headers=headers).json()["status"] == "completed"
    course = next(course for course in client.get("/api/courses").json() if course["id"] == "python-data-science")
    endpoint = f"/api/learning-plan/{course['id']}"
    saved = client.put(endpoint, json={"status": "saved"}, headers=headers).json()
    assert saved["completed_at"] is None
    completed = client.put(endpoint, json={"status": "completed"}, headers=headers).json()
    again = client.put(endpoint, json={"status": "completed"}, headers=headers).json()
    assert completed["completed_at"] == again["completed_at"]
    assert completed["saved_at"] == saved["saved_at"]
    profile = client.get("/api/profile").json()
    assert profile["skills"].count("Python") == 1
    assert profile["training_history"].count(course["title"]) == 1
    assert client.get("/api/recommendations").json() == []
    assert client.get("/api/notifications").json() == []
    assert client.put(endpoint, json={"status": "unknown"}, headers=headers).status_code == 422
    assert client.delete(endpoint, headers=headers).status_code == 200
    assert client.get("/api/learning-plan").json() == []
    # Removing a plan entry does not erase an employee's acquired training history.
    assert course["title"] in client.get("/api/profile").json()["training_history"]


def test_roles_admin_ingestion_and_course_validation(client):
    headers = login(client)
    course = client.get("/api/courses").json()[0]
    payload = {key: value for key, value in course.items() if key in config.CourseInput.model_fields}
    assert client.get("/api/admin/overview").status_code == 403
    assert client.post("/api/admin/courses", json=payload, headers=headers).status_code == 403
    headers = login(client, "hr")
    overview = client.get("/api/admin/overview")
    assert overview.status_code == 200
    assert "email" not in overview.text and "career_goal" not in overview.text
    assert client.post("/api/admin/courses", json=payload, headers=headers).status_code == 403
    headers = login(client, "admin")
    assert client.post("/api/admin/courses", json={**payload, "url": "javascript:alert(1)"}, headers=headers).status_code == 422
    assert client.post("/api/admin/courses", json={**payload, "discount_percent": 99}, headers=headers).status_code == 422
    created = client.post("/api/admin/courses", json=payload, headers=headers)
    assert created.status_code == 200, created.text
    assert client.get(f"/api/courses/{created.json()['id']}").status_code == 200
    post = {"text": "I completed a Python course this week.", "source": "Consented project example", "is_demo": True}
    assert client.post("/api/admin/posts", json=post, headers=headers).status_code == 200
    assert client.post("/api/admin/posts", json={**post, "published_at": "2099-01-01T00:00:00+00:00"}, headers=headers).status_code == 422


def test_privacy_export_is_complete_without_secrets_and_delete_cascades(client):
    user, headers = register(client)
    uid = user["user"]["id"]
    for index in range(25):
        db.save_run(uid, {"id": str(index), "status": "completed", "started_at": config.utcnow(), "steps": []})
    exported = client.get("/api/privacy/export")
    assert len(exported.json()["runs"]) == 25
    assert exported.headers["cache-control"] == "no-store"
    assert "password_hash" not in exported.text and "csrf_token" not in exported.text
    assert client.request("DELETE", "/api/privacy/account", json={"password": "wrong"}, headers=headers).status_code == 401
    token = client.cookies.get(api.COOKIE)
    assert client.request("DELETE", "/api/privacy/account", json={"password": "StrongPass123!"}, headers=headers).status_code == 200
    assert db.user_by_id(uid) is None and db.session_get(security.digest_token(token)) is None
    assert db.runs(uid) == []
    assert client.get("/api/auth/session").status_code == 401
    headers = login(client, "admin")
    assert client.request("DELETE", "/api/privacy/account", json={"password": "SkillScout123!"}, headers=headers).status_code == 409


def test_expired_session_is_rejected(client):
    login(client)
    with db.connection() as conn:
        conn.execute("UPDATE sessions SET expires_at=?", ((datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),))
    assert client.get("/api/auth/session").status_code == 401


def test_body_size_limits_include_streaming_and_delete(client):
    response = client.post("/api/auth/login", content=(b"x" * 800000 for _ in range(2)), headers={"Content-Type": "application/json"})
    assert response.status_code == 413
    assert client.request("DELETE", "/api/privacy/account", content=b"x" * 1_500_001).status_code == 413


def test_scheduler_respects_opt_in_recent_manual_runs_and_no_duplicate_notices(client, agent_http, monkeypatch):
    headers = login(client)
    assert client.post("/api/runs", headers=headers).json()["status"] == "completed"
    monkeypatch.setenv("SKILLSCOUT_SCHEDULER_ENABLED", "true")
    count = len(agent_http)
    asyncio.run(api.scheduler_tick())
    assert len(agent_http) == count
    uid = db.user_by_email("alex@skillscout.demo")["id"]
    with db.connection() as conn:
        rows = conn.execute("SELECT id,data_json FROM runs WHERE user_id=?", (uid,)).fetchall()
        for row in rows:
            run = json.loads(row["data_json"])
            run["started_at"] = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
            conn.execute("UPDATE runs SET started_at=?,data_json=? WHERE id=?", (run["started_at"], db.dump(run), row["id"]))
    asyncio.run(api.scheduler_tick())
    assert len(agent_http) == count + 4
    assert api.SCHEDULER_LAST
    assert len(db.runs(uid)) == 2


def test_worker_credentials_contract_identity_and_success(client, monkeypatch):
    monkeypatch.setenv("AGENT_KIND", "profile")
    user = db.user_by_email("alex@skillscout.demo")
    envelope = {"run_id": "test-run", "user_id": user["id"], "payload": {"profile": db.profile(user)}}
    with TestClient(worker.app) as service:
        assert service.get("/health").json() == {"status": "ok", "kind": "profile"}
        assert service.post("/execute", json=envelope).status_code == 401
        headers = {"X-Agent-Key": "test-agent-secret"}
        assert service.post("/execute", json={**envelope, "payload": {}}, headers=headers).status_code == 422
        assert service.post("/execute", json={**envelope, "user_id": "someone-else"}, headers=headers).status_code == 422
        response = service.post("/execute", json=envelope, headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["run_id"] == "test-run"
        assert "Python" in response.json()["result"]["skill_gaps"]


@pytest.mark.parametrize("change", ["wrong-run", "wrong-agent", "missing-result", "invalid-result"])
def test_agent_response_correlation_and_shape(client, monkeypatch, change):
    original_client = httpx.AsyncClient
    body = {"run_id": "run", "agent": "profile", "result": api._empty_needs_for_search()}
    if change == "wrong-run": body["run_id"] = "other"
    if change == "wrong-agent": body["agent"] = "trends"
    if change == "missing-result": body.pop("result")
    if change == "invalid-result": body["result"] = None
    monkeypatch.setattr(api.httpx, "AsyncClient", lambda **kwargs: original_client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body)), **kwargs))
    with pytest.raises(RuntimeError):
        asyncio.run(api.call_agent("profile", 8101, "run", "user", {"profile": {}}))


def test_unknown_course_from_agent_is_rejected_and_known_facts_restored(client):
    course = db.items("courses")[0]
    with pytest.raises(RuntimeError, match="unknown course"):
        api._validate_agent_result("retrieval", [{"course": {"id": "invented"}}], {"courses": [course]})
    result = api._validate_agent_result("retrieval", [{"course": {**course, "url": "https://untrusted.example"}}], {"courses": [course]})
    assert result[0]["course"]["url"] == course["url"]


def test_expired_offers_are_normalized_across_catalogue_detail_plan(client):
    headers = login(client)
    course = next(course for course in db.items("courses") if course["id"] == "nlp-specialization")
    assert course["discount_percent"] == 0
    assert course["price"] == course["original_price"]
    assert client.get("/api/courses/nlp-specialization").json()["discount_percent"] == 0
    client.put("/api/learning-plan/nlp-specialization", json={"status": "saved"}, headers=headers)
    assert client.get("/api/learning-plan").json()[0]["course"]["discount_percent"] == 0


def test_saved_analysis_and_notices_stop_claiming_an_expired_discount(client, agent_http):
    headers = login(client)
    assert client.post('/api/runs', headers=headers).json()['status'] == 'completed'
    uid = db.user_by_email('alex@skillscout.demo')['id']
    with db.connection() as conn:
        row = conn.execute('SELECT data_json FROM analyses WHERE user_id=?', (uid,)).fetchone()
        value = json.loads(row[0])
        rec = next(r for r in value['recommendations'] if r['course']['id'] == 'python-data-science')
        rec['course']['offer_expires_at'] = '2020-01-01T00:00:00+00:00'
        conn.execute('UPDATE analyses SET data_json=? WHERE user_id=?', (db.dump(value), uid))
        conn.execute('UPDATE courses SET data_json=? WHERE id=?', (db.dump(rec['course']), rec['course']['id']))
    fresh = next(r for r in client.get('/api/recommendations').json() if r['id'] == 'python-data-science')
    assert fresh['course']['price'] == 99
    assert fresh['factors']['discount_value'] == 0
    assert '70% sample discount is listed' not in fresh['explanation']
    assert 'expired offer' in fresh['explanation']
    notice = next(n for n in client.get('/api/notifications').json() if n['course_id'] == 'python-data-science')
    assert 'expired' in notice['title']
    assert 'USD 99' in notice['message']
