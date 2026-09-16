#!/usr/bin/env python3
"""Exercise the running services over HTTP with a disposable employee account."""
from pathlib import Path
import argparse
import json
import sys
import time
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--require-llm", action="store_true")
    args = parser.parse_args()
    password = "SmokeOnly-" + uuid4().hex
    started = time.monotonic()
    report = {"transport": "real HTTP", "checks": []}
    with httpx.Client(base_url=args.url, timeout=150, trust_env=False) as client:
        def call(method, path, body=None):
            response = client.request(method, "/api" + path, **({"json": body} if body is not None else {}))
            response.raise_for_status()
            return response.json()
        assert call("GET", "/health")["status"] == "ok"
        account = call("POST", "/auth/register", {"email": f"smoke-{uuid4().hex[:10]}@example.test", "name": "Smoke Test", "password": password})
        client.headers["X-CSRF-Token"] = account["csrf_token"]
        try:
            profile = call("GET", "/profile")
            blocked = client.post("/api/runs", json={})
            assert blocked.status_code == 403, blocked.text
            report["checks"].append("consent enforced")
            profile.update(role_title="Data Analyst", career_goal="Data Scientist", skills=["SQL", "Excel", "Power BI"], experience_years=3, weekly_hours=6, budget=80, consent=True, notifications_enabled=True)
            call("PUT", "/profile", profile)
            system = call("GET", "/system")
            assert len(system["agents"]) == 4 and all(a["status"] == "online" for a in system["agents"]), system
            run = call("POST", "/runs", {})
            assert run["status"] == "completed", run
            assert [s["agent"] for s in run["steps"]] == ["profile", "trends", "retrieval", "recommendations"]
            assert all(s["status"] == "completed" for s in run["steps"])
            report["checks"].append("four independent HTTP agents complete")
            dashboard = call("GET", "/dashboard")
            assert "Python" in dashboard["needs"]["skill_gaps"]
            recommendations = dashboard["recommendations"]
            assert recommendations and all(0 <= r["score"] <= 100 for r in recommendations)
            if args.require_llm:
                assert dashboard["needs"]["llm_used"], dashboard["needs"]
            report["profile_llm_used"] = dashboard["needs"]["llm_used"]
            report["recommendations"] = len(recommendations)
            course = recommendations[0]["course"]
            for status in ["saved", "in_progress", "completed"]:
                item = call("PUT", "/learning-plan/" + course["id"], {"status": status})
                assert item["status"] == status
            report["checks"].append("save/start/complete persisted")
            results = call("GET", "/courses?q=Python")
            assert results and any("Python" in c["skills"] for c in results[:3])
            assert not call("GET", "/courses?q=zzzzmissingsearchterm")
            answer = call("POST", "/chat", {"message": "Which beginner Python course should I learn next?"})
            assert answer["answer"] and answer["sources"]
            if args.require_llm:
                assert answer["llm_used"], answer
            report["chat_llm_used"] = answer["llm_used"]
            report["checks"].append("retrieval and grounded chat")
            assert client.get("/api/admin/overview").status_code == 403
            exported = call("GET", "/privacy/export")
            assert "password_hash" not in json.dumps(exported)
            assert exported["user"]["id"] == account["user"]["id"]
            report["checks"].append("RBAC and private export")
            call("POST", "/notifications/all/read", {})
        finally:
            call("DELETE", "/privacy/account", {"password": password})
            assert client.get("/api/auth/session").status_code == 401
    report["checks"].append("account deletion invalidates session")
    report["seconds"] = round(time.monotonic() - started, 2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
