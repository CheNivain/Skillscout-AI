"""Shared fixtures for the SkillScout test suite."""
from __future__ import annotations

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from backend import api, config, security
from backend.ai import engine


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SKILLSCOUT_DB_PATH", str(tmp_path / "workspace.db"))
    monkeypatch.setenv("SKILLSCOUT_SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("SKILLSCOUT_SEED_DEMO", "true")
    monkeypatch.setenv("SKILLSCOUT_AGENT_KEY", "test-agent-secret")
    monkeypatch.setattr(security, "limiter", security.RateLimiter())
    monkeypatch.setattr(engine, "_complete_llm", lambda *args, **kwargs: (None, None))
    monkeypatch.setattr(
        engine,
        "get_model_status",
        lambda: {
            "llm_available": False,
            "provider": "ollama",
            "model": "test",
            "description": "Offline test",
        },
    )
    with TestClient(api.app) as session:
        yield session


def login(client, role: str = "alex") -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"email": f"{role}@skillscout.demo", "password": "SkillScout123!"},
    )
    assert response.status_code == 200, response.text
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def register(client, email: str = "learner@example.com", password: str = "StrongPass123!"):
    response = client.post(
        "/api/auth/register",
        json={"name": "New Learner", "email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json(), {"X-CSRF-Token": response.json()["csrf_token"]}


@pytest.fixture
def agent_http(monkeypatch):
    """Simulate worker HTTP while still executing the real agent algorithms."""
    called: list[str] = []
    original_client = httpx.AsyncClient

    async def handler(request):
        envelope = json.loads(request.content)
        kind = dict((port, kind) for kind, _, port, _ in config.AGENTS)[request.url.port]
        assert request.headers["x-agent-key"] == "test-agent-secret"
        assert envelope["user_id"]
        called.append(kind)
        functions = {
            "profile": engine.analyze_profile,
            "trends": engine.discover_trends,
            "retrieval": engine.retrieve_courses,
            "recommendations": engine.recommend,
        }
        result = functions[kind](**envelope["payload"])
        return httpx.Response(200, json={"run_id": envelope["run_id"], "agent": kind, "result": result})

    monkeypatch.setattr(
        api.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    return called


@pytest.fixture
def data_analyst_profile():
    return {
        "role_title": "Data Analyst",
        "career_goal": "Data Scientist",
        "skills": ["SQL", "Excel", "Power BI"],
        "certifications": [],
        "training_history": [],
        "experience_years": 3,
        "weekly_hours": 6,
        "budget": 80,
        "interests": [],
        "bio": "",
        "consent": True,
        "notifications_enabled": True,
    }
