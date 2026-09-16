"""Gateway HTTP API: auth, orchestration of four agent services, and the employee workspace."""
from __future__ import annotations

import asyncio
import hmac
import json
import logging
import os
import re
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from backend import config, db, security
from backend.ai import engine
from backend.config import CourseInput, PostInput, ProfileInput
from backend.data.seed import CORPUS_NOTE

logger = logging.getLogger(__name__)
COOKIE = "skillscout_session"
DIST = config.ROOT / "frontend" / "dist"
SCHEDULER_LAST: str | None = None
RUNNING_USERS: set[str] = set()
PIPELINE_TIMEOUT = 120
PRICING = [
    {"name": "Starter", "price_lkr": 300, "description": "Small organisations · LKR 300 per active employee / month · local workspace"},
    {"name": "Professional", "price_lkr": 550, "description": "Medium organisations · LKR 550 per active employee / month · HR analytics"},
    {"name": "Enterprise", "price_lkr": 800, "description": "Large organisations · from LKR 800 per active employee / month · LMS/HRIS integrations, negotiated"},
]


class CredentialInput(BaseModel):
    # Password spaces are significant, while names and addresses are normalized.
    model_config = ConfigDict(extra="forbid")


class LoginIn(CredentialInput):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def email_address(cls, value: str) -> str:
        value = value.strip().casefold()
        if not re.fullmatch(r"[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+", value):
            raise ValueError("Provide a valid email address")
        return value


class RegisterIn(LoginIn):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("name")
    @classmethod
    def display_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Provide a name with at least two characters")
        return value


class PlanIn(config.StrictModel):
    status: Literal["saved", "in_progress", "completed"]


class ChatIn(config.StrictModel):
    message: str = Field(min_length=1, max_length=800)


class DeleteIn(CredentialInput):
    password: str = Field(min_length=1, max_length=128)


def _cookie_secure() -> bool:
    return os.environ.get("SKILLSCOUT_SECURE_COOKIE", "false").lower() == "true"


def _client_key(request: Request) -> str:
    # Forwarded headers are not trusted by the local gateway.
    return request.client.host if request.client else "local"


def _set_session(response: Response, token: str) -> None:
    response.set_cookie(COOKIE, token, httponly=True, samesite="lax", secure=_cookie_secure(), max_age=60 * 60 * 24, path="/")


def _clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE, path="/")


def current_user(request: Request) -> dict:
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, "Please sign in")
    row = db.session_get(security.digest_token(token))
    if not row:
        raise HTTPException(401, "Your session expired. Please sign in again.")
    return row


def require_csrf(request: Request, user: dict) -> None:
    supplied = request.headers.get("x-csrf-token", "")
    if not supplied or not hmac.compare_digest(supplied, user["csrf_token"]):
        raise HTTPException(403, "Missing or invalid CSRF token")


def require_roles(user: dict, *roles: str) -> None:
    if user["role"] not in roles:
        raise HTTPException(403, "You do not have access to this area")


async def _agent_health(kind: str, port: int) -> str:
    url = config.agent_url(kind, port)
    try:
        async with httpx.AsyncClient(timeout=1.5, trust_env=False) as client:
            response = await client.get(url + "/health")
            if response.status_code == 200:
                data = response.json()
                if data.get("kind") != kind:
                    return "error"
                return "online" if data.get("status") == "ok" else "unconfigured"
            return "error"
    except Exception:
        return "offline"


async def call_agent(kind: str, port: int, run_id: str, user_id: str, payload: dict) -> dict:
    url = config.agent_url(kind, port) + "/execute"
    headers = {"X-Agent-Key": config.agent_key(), "Content-Type": "application/json"}
    body = {"run_id": run_id, "user_id": user_id, "payload": payload}
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=3.0), trust_env=False) as client:
                response = await client.post(url, headers=headers, json=body)
            if response.status_code >= 400:
                detail = "Agent request failed"
                try:
                    detail = str(response.json().get("detail") or detail)
                except Exception:
                    pass
                raise RuntimeError(detail)
            data = response.json()
            if not isinstance(data, dict) or data.get("agent") != kind or data.get("run_id") != run_id or "result" not in data:
                raise RuntimeError("Unexpected agent response")
            return _validate_agent_result(kind, data["result"], payload)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadError) as exc:
            last_error = exc
            if attempt == 0:
                await asyncio.sleep(0.4)
                continue
            raise RuntimeError(f"Could not reach the {kind} agent") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"The {kind} agent returned a transport error") from exc
    raise RuntimeError(str(last_error or "Agent call failed"))


def _validate_agent_result(kind: str, result: Any, payload: dict):
    """Reject malformed/misattributed data before it can enter a persisted analysis."""
    if kind == "profile":
        fields = ("current_skills", "target_skills", "skill_gaps", "priority_skills")
        if not isinstance(result, dict) or not all(isinstance(result.get(key), list) and all(isinstance(x, str) for x in result[key]) for key in fields):
            raise RuntimeError("The profile agent returned invalid training needs")
    else:
        if not isinstance(result, list) or len(result) > 2000 or any(not isinstance(row, dict) for row in result):
            raise RuntimeError(f"The {kind} agent returned invalid results")
        if kind == "trends" and any(not isinstance(row.get("skill"), str) or not isinstance(row.get("evidence"), list) for row in result):
            raise RuntimeError("The trends agent returned invalid evidence")
        if kind in {"retrieval", "recommendations"}:
            source = payload.get("courses", []) if kind == "retrieval" else [row["course"] for row in payload["candidates"]]
            catalogue = {course["id"]: course for course in source}
            for row in result:
                course = row.get("course")
                if not isinstance(course, dict) or course.get("id") not in catalogue:
                    raise RuntimeError(f"The {kind} agent returned an unknown course")
                # Course facts always come from the retrieved catalogue, never a generated response.
                row["course"] = catalogue[course["id"]]
                if kind == "recommendations":
                    score = row.get("score")
                    factors = row.get("factors")
                    if not isinstance(score, (int, float)) or not 0 <= score <= 100 or not isinstance(factors, dict) or any(not isinstance(value, (int, float)) or not 0 <= value <= 100 for value in factors.values()):
                        raise RuntimeError("The recommendation agent returned invalid scores")
                    if row.get("priority") not in {"high", "medium", "low"} or not isinstance(row.get("explanation"), str):
                        raise RuntimeError("The recommendation agent returned invalid explanations")
    return result


def _notices_from(recommendations: list[dict]) -> list[dict]:
    notices = []
    for rec in recommendations:
        if rec.get("priority") != "high" or rec.get("score", 0) < 75:
            continue
        course = rec["course"]
        offer = course.get("discount_percent") if rec["factors"].get("discount_value", 0) >= 50 else 0
        title = "Limited-time learning opportunity" if offer else "High-priority learning opportunity"
        message = rec.get("explanation") or f"{course['title']} matches your current goals."
        notices.append({
            "id": str(uuid4()),
            "title": title,
            "message": message,
            "course_id": course["id"],
            "created_at": config.utcnow(),
            "read": False,
            "kind": "opportunity",
            "dedupe_key": f"{course['id']}:{course.get('price')}:{course.get('offer_expires_at')}",
        })
    return notices[:8]


async def execute_pipeline(user: dict) -> dict:
    """Serialize each employee's manual and scheduled work in this gateway process."""
    uid = user["id"]
    if uid in RUNNING_USERS:
        raise HTTPException(409, "A learning analysis is already running for your account")
    user = db.user_by_id(uid)
    if not user:
        raise HTTPException(401, "Please sign in again")
    profile = db.profile(user)
    if not profile.get("consent"):
        raise HTTPException(403, "Enable learning analysis in your profile before running the agents")
    if not profile.get("role_title") or not profile.get("career_goal"):
        raise HTTPException(400, "Add your current role and career goal in your profile first")
    RUNNING_USERS.add(uid)
    try:
        try:
            return await asyncio.wait_for(_execute_pipeline(user), timeout=PIPELINE_TIMEOUT)
        except TimeoutError:
            # _execute_pipeline persists its interrupted trace before cancellation propagates.
            latest = db.runs(uid, 1)
            if latest:
                return latest[0]
            raise HTTPException(504, "Learning analysis timed out. Please try again.") from None
    finally:
        RUNNING_USERS.discard(uid)


async def _execute_pipeline(user: dict) -> dict:
    rid = str(uuid4())
    started = config.utcnow()
    profile = db.profile(user)
    steps = [
        {"agent": kind, "label": label, "status": "pending", "duration_ms": 0, "input": {}, "output": {}, "error": None}
        for kind, label, _, _ in config.AGENTS
    ]
    run = {"id": rid, "status": "running", "started_at": started, "finished_at": None, "error": None, "steps": steps}
    db.save_run(user["id"], run)
    context: dict[str, Any] = {"profile": profile, "posts": db.items("posts"), "courses": db.items("courses")}
    builders = {
        "profile": lambda: {"profile": context["profile"]},
        "trends": lambda: {"posts": context["posts"], "needs": context["needs"]},
        "retrieval": lambda: {"courses": context["courses"], "needs": context["needs"], "trends": context["trends"]},
        "recommendations": lambda: {"profile": context["profile"], "needs": context["needs"], "trends": context["trends"], "candidates": context["candidates"]},
    }
    try:
        for index, (kind, _label, port, _desc) in enumerate(config.AGENTS):
            latest_user = db.user_by_id(user["id"])
            if not latest_user or latest_user["profile_version"] != user["profile_version"] or not db.profile(latest_user).get("consent"):
                raise RuntimeError("Your profile changed or consent was withdrawn before results could be saved.")
            step = steps[index]
            step["status"] = "running"
            payload = builders[kind]()
            step["input"] = {key: (f"{len(value)} items" if isinstance(value, list) else value) for key, value in payload.items()}
            db.save_run(user["id"], run)
            t0 = asyncio.get_event_loop().time()
            result = await call_agent(kind, port, rid, user["id"], payload)
            step["duration_ms"] = int((asyncio.get_event_loop().time() - t0) * 1000)
            step["status"] = "completed"
            if kind == "profile":
                context["needs"] = result
                step["output"] = {"skill_gaps": result.get("skill_gaps"), "llm_used": result.get("llm_used")}
            elif kind == "trends":
                context["trends"] = result
                step["output"] = {"count": len(result or [])}
            elif kind == "retrieval":
                context["candidates"] = result
                step["output"] = {"count": len(result or [])}
            else:
                context["recommendations"] = result
                step["output"] = {"count": len(result or [])}
            db.save_run(user["id"], run)
        analysis = {
            "needs": context["needs"],
            "trends": context["trends"],
            "recommendations": context["recommendations"],
        }
        committed = db.commit_analysis(user["id"], user["profile_version"], analysis, _notices_from(context["recommendations"]))
        if not committed:
            raise RuntimeError("Your profile changed or consent was withdrawn before results could be saved.")
        run.update(status="completed", finished_at=config.utcnow())
        db.save_run(user["id"], run)
        return run
    except (Exception, asyncio.CancelledError) as exc:
        if isinstance(exc, asyncio.CancelledError):
            message = "Learning analysis was interrupted or exceeded its time limit. Please try again."
        else:
            logger.exception("Run %s failed", rid)
            message = str(exc)[:400] or "Learning analysis could not complete. Please try again."
        for step in steps:
            if step["status"] in ("pending", "running"):
                step.update(status="failed", error=message)
        run.update(status="failed", finished_at=config.utcnow(), error=message)
        db.save_run(user["id"], run)
        if isinstance(exc, asyncio.CancelledError):
            raise
        return run


async def scheduler_tick():
    global SCHEDULER_LAST
    SCHEDULER_LAST = config.utcnow()
    if not config.scheduler_enabled():
        return
    for user in db.all_users():
        profile = db.profile(user)
        if user["role"] != "employee" or not profile.get("consent") or not profile.get("notifications_enabled") or not profile.get("role_title") or not profile.get("career_goal"):
            continue
        latest = db.runs(user["id"], 1)
        if user["id"] in RUNNING_USERS:
            continue
        if latest:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(latest[0]["started_at"])).total_seconds()
            if age < config.scheduler_minutes() * 60:
                continue
        try:
            await execute_pipeline(user)
        except Exception:
            logger.exception("Scheduled run failed for %s", user["id"])


async def scheduler_loop():
    await asyncio.sleep(8)
    while True:
        try:
            await scheduler_tick()
        except Exception:
            logger.exception("Scheduler tick failed; it will retry at the next interval")
        await asyncio.sleep(config.scheduler_minutes() * 60)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global SCHEDULER_LAST
    SCHEDULER_LAST = None
    RUNNING_USERS.clear()
    db.initialize()
    task = asyncio.create_task(scheduler_loop()) if config.scheduler_enabled() else None
    yield
    if task:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass


app = FastAPI(title="SkillScout AI", version=config.VERSION, lifespan=lifespan, docs_url=None, redoc_url=None)
app.add_middleware(security.BodyLimitMiddleware)


@app.exception_handler(HTTPException)
async def http_error(_request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else json.dumps(exc.detail)
    return JSONResponse({"detail": detail}, status_code=exc.status_code, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error(_request, exc: RequestValidationError):
    # Pydantic's default response includes rejected input, which may be a password.
    errors = [f"{'.'.join(str(part) for part in error['loc'] if part != 'body') or 'request'}: {error['msg']}" for error in exc.errors()[:4]]
    return JSONResponse({"detail": "; ".join(errors)}, status_code=422)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    if request.url.path.startswith("/api/") and request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        allowed = {f"http://{host}:{port}" for host in ("localhost", "127.0.0.1", "[::1]") for port in (5173, 8000)}
        allowed.update(value.strip().rstrip("/") for value in os.environ.get("SKILLSCOUT_ALLOWED_ORIGINS", "").split(",") if value.strip())
        if origin and origin.rstrip("/") not in allowed:
            return JSONResponse({"detail": "This browser origin is not allowed"}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


def _auth_payload(user: dict, token: str | None = None, response: Response | None = None) -> dict:
    csrf = user.get("csrf_token")
    if token and response is not None:
        csrf = security.new_token()
        db.session_create(user["id"], security.digest_token(token), csrf)
        _set_session(response, token)
    return {"user": db.public_user(user), "csrf_token": csrf}


@app.get("/api/health")
def health():
    return {"status": "ok", "version": config.VERSION}


@app.post("/api/auth/login")
def login(body: LoginIn, request: Request, response: Response):
    if not security.limiter.allow("login:" + _client_key(request), 8, 60):
        raise HTTPException(429, "Too many sign-in attempts. Please wait a minute.")
    user = db.user_by_email(str(body.email))
    if not user or not security.verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Incorrect email or password")
    if previous := request.cookies.get(COOKIE):
        db.session_delete(security.digest_token(previous))
    token = security.new_token()
    return _auth_payload(user, token, response)


@app.post("/api/auth/register")
def register(body: RegisterIn, request: Request, response: Response):
    if not security.limiter.allow("register:" + _client_key(request), 5, 3600):
        raise HTTPException(429, "Too many new accounts from this address")
    if db.user_by_email(str(body.email)):
        raise HTTPException(409, "An account with this email already exists")
    try:
        user = db.create_user(body.name, body.email, body.password)
    except sqlite3.IntegrityError:
        raise HTTPException(409, "An account with this email already exists") from None
    if previous := request.cookies.get(COOKIE):
        db.session_delete(security.digest_token(previous))
    token = security.new_token()
    return _auth_payload(user, token, response)


@app.get("/api/auth/session")
def session(request: Request):
    user = current_user(request)
    return {"user": db.public_user(user), "csrf_token": user["csrf_token"]}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response):
    user = current_user(request)
    require_csrf(request, user)
    token = request.cookies.get(COOKIE)
    if token:
        db.session_delete(security.digest_token(token))
    _clear_session(response)
    return {"ok": True}


def _mode() -> dict:
    return engine.get_model_status()


def _stats(uid: str, analysis: dict) -> dict:
    plan = db.plan(uid)
    notes = db.notifications(uid)
    return {
        "recommendations": len(analysis.get("recommendations") or []),
        "skill_gaps": len((analysis.get("needs") or {}).get("skill_gaps") or []),
        "saved_courses": sum(1 for item in plan if item["status"] != "completed"),
        "completed_courses": sum(1 for item in plan if item["status"] == "completed"),
        "unread_notifications": sum(1 for item in notes if not item.get("read")),
    }


@app.get("/api/profile")
def get_profile(request: Request):
    user = current_user(request)
    return db.profile(user)


@app.put("/api/profile")
def put_profile(request: Request, body: ProfileInput):
    user = current_user(request)
    require_csrf(request, user)
    profile = body.model_dump()
    profile["user_id"] = user["id"]
    db.save_profile(user["id"], profile)
    return profile


@app.get("/api/dashboard")
def dashboard(request: Request):
    user = current_user(request)
    profile = db.profile(user)
    analysis = db.analysis(user["id"])
    runs = db.runs(user["id"], 1)
    return {
        "profile": profile,
        "needs": analysis.get("needs"),
        "recommendations": analysis.get("recommendations") or [],
        "trends": analysis.get("trends") or [],
        "stats": _stats(user["id"], analysis),
        "last_run": runs[0] if runs else None,
        "mode": _mode(),
    }


@app.post("/api/runs")
async def start_run(request: Request):
    user = current_user(request)
    require_csrf(request, user)
    if not security.limiter.allow("run:" + user["id"], 6, 60):
        raise HTTPException(429, "Please wait a minute before starting another analysis")
    return await execute_pipeline(user)


@app.get("/api/runs")
def list_runs(request: Request):
    user = current_user(request)
    return db.runs(user["id"], 20)


@app.get("/api/runs/{rid}")
def get_run(rid: str, request: Request):
    user = current_user(request)
    run = db.get_run(user["id"], rid)
    if not run:
        raise HTTPException(404, "Run not found")
    return run


@app.get("/api/courses")
def list_courses(request: Request, q: str | None = Query(default=None, max_length=300), category: str | None = Query(default=None, max_length=120), level: str | None = Query(default=None, max_length=120), kind: str | None = Query(default=None, max_length=120), free_only: bool = False):
    current_user(request)
    courses = db.items("courses")
    if category:
        courses = [c for c in courses if c.get("category", "").casefold() == category.casefold()]
    if level:
        courses = [c for c in courses if c.get("level") == level]
    if kind:
        courses = [c for c in courses if c.get("kind") == kind]
    if free_only:
        courses = [c for c in courses if not c.get("price")]
    if q:
        analysis = {"needs": _empty_needs_for_search()}
        ranked = engine.retrieve_courses(courses, analysis["needs"], [], query=q, limit=40)
        return [row["course"] for row in ranked]
    return courses


def _empty_needs_for_search() -> dict:
    return {
        "current_role": "", "career_goal": "", "current_skills": [], "target_skills": [],
        "skill_gaps": [], "priority_skills": [], "summary": "", "llm_used": False, "model": None,
    }


@app.get("/api/courses/{cid}")
def get_course(cid: str, request: Request):
    current_user(request)
    course = db.item("courses", cid)
    if not course:
        raise HTTPException(404, "Course not found")
    return course


@app.get("/api/recommendations")
def recommendations(request: Request):
    user = current_user(request)
    return db.analysis(user["id"]).get("recommendations") or []


@app.get("/api/trends")
def trends(request: Request):
    user = current_user(request)
    analysis = db.analysis(user["id"])
    return {"trends": analysis.get("trends") or [], "posts": db.items("posts"), "corpus_note": CORPUS_NOTE}


@app.get("/api/learning-plan")
def learning_plan(request: Request):
    user = current_user(request)
    return db.plan(user["id"])


@app.put("/api/learning-plan/{course_id}")
def put_plan(course_id: str, body: PlanIn, request: Request):
    user = current_user(request)
    require_csrf(request, user)
    course = db.item("courses", course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    try:
        return db.save_plan(user["id"], course, body.status)
    except ValidationError:
        raise HTTPException(409, "Your profile has reached its skill or history limit. Review your profile before adding more completed training.") from None
    except ValueError:
        raise HTTPException(409, "Your profile has reached its supported entry limit. Review your skills and training history before recording another completion.") from None


@app.delete("/api/learning-plan/{course_id}")
def delete_plan(course_id: str, request: Request):
    user = current_user(request)
    require_csrf(request, user)
    db.delete_plan(user["id"], course_id)
    return {"ok": True}


@app.get("/api/notifications")
def notifications(request: Request):
    user = current_user(request)
    return db.notifications(user["id"])


@app.post("/api/notifications/{nid}/read")
def read_notification(nid: str, request: Request):
    user = current_user(request)
    require_csrf(request, user)
    if not db.mark_read(user["id"], nid):
        raise HTTPException(404, "Notification not found")
    return {"ok": True}


@app.get("/api/system")
async def system(request: Request):
    current_user(request)
    statuses = await asyncio.gather(*(_agent_health(kind, port) for kind, _, port, _ in config.AGENTS))
    agents = [{"id": kind, "name": name, "port": port, "status": status, "description": description} for (kind, name, port, description), status in zip(config.AGENTS, statuses)]
    return {
        "agents": agents,
        "mode": _mode(),
        "scheduler": {"enabled": config.scheduler_enabled(), "interval_minutes": config.scheduler_minutes(), "last_checked_at": SCHEDULER_LAST},
        "catalogue_count": len(db.items("courses")),
        "post_count": len(db.items("posts")),
    }


@app.post("/api/chat")
def chat(body: ChatIn, request: Request):
    user = current_user(request)
    require_csrf(request, user)
    profile = db.profile(user)
    if not profile.get("consent"):
        raise HTTPException(403, "Enable learning analysis in your profile before asking Scout")
    if not security.limiter.allow("chat:" + user["id"], 12, 60):
        raise HTTPException(429, "Please wait a minute before asking Scout again")
    analysis = db.analysis(user["id"])
    return engine.answer_question(body.message, profile, db.items("courses"), analysis.get("needs"))


@app.get("/api/privacy/export")
def export_me(request: Request):
    user = current_user(request)
    return {
        "user": db.public_user(user),
        "profile": db.profile(user),
        "learning_plan": db.plan(user["id"]),
        "runs": db.runs(user["id"], None),
        "notifications": db.notifications(user["id"], None),
        "analysis": db.analysis(user["id"]),
    }


@app.delete("/api/privacy/account")
def delete_account(body: DeleteIn, request: Request, response: Response):
    user = current_user(request)
    require_csrf(request, user)
    if not security.verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Incorrect password")
    if not db.delete_user(user["id"]):
        raise HTTPException(409, "The last administrator account cannot be deleted")
    _clear_session(response)
    return {"ok": True}


@app.get("/api/admin/overview")
def overview(request: Request):
    user = current_user(request)
    require_roles(user, "hr", "admin")
    employees = [u for u in db.all_users() if u["role"] == "employee"]
    gaps: dict[str, int] = {}
    roles: dict[str, int] = {}
    recs = 0
    completed = 0
    active = 0
    for emp in employees:
        profile = db.profile(emp)
        role = profile.get("role_title") or "Unspecified"
        roles[role] = roles.get(role, 0) + 1
        analysis = db.analysis(emp["id"])
        recs += len(analysis.get("recommendations") or [])
        for skill in (analysis.get("needs") or {}).get("skill_gaps") or []:
            gaps[skill] = gaps.get(skill, 0) + 1
        plan = db.plan(emp["id"])
        completed += sum(1 for item in plan if item["status"] == "completed")
        if any(item["status"] == "in_progress" for item in plan) or analysis.get("recommendations"):
            active += 1
    return {
        "employee_count": len(employees),
        "active_learners": active,
        "completed_courses": completed,
        "total_recommendations": recs,
        "top_skill_gaps": [{"skill": k, "count": v} for k, v in sorted(gaps.items(), key=lambda kv: -kv[1])[:8]],
        "role_distribution": [{"role": k, "count": v} for k, v in sorted(roles.items(), key=lambda kv: -kv[1])],
        "catalogue_count": len(db.items("courses")),
        "post_count": len(db.items("posts")),
        "pricing": PRICING,
    }


@app.post("/api/admin/courses")
def add_course(body: CourseInput, request: Request):
    user = current_user(request)
    require_csrf(request, user)
    require_roles(user, "admin")
    course = body.model_dump()
    course["id"] = "course-" + uuid4().hex[:10]
    return db.add_item("courses", course)


@app.post("/api/admin/posts")
def add_post(body: PostInput, request: Request):
    user = current_user(request)
    require_csrf(request, user)
    require_roles(user, "admin")
    post = body.model_dump()
    post["id"] = "post-" + uuid4().hex[:10]
    return db.add_item("posts", post)


if DIST.exists():
    assets = DIST / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        target = (DIST / path).resolve()
        if not target.is_relative_to(DIST.resolve()):
            raise HTTPException(404, "Not found")
        if path and target.is_file():
            return FileResponse(target)
        index = DIST / "index.html"
        if index.exists() and not path.startswith("api"):
            return FileResponse(index)
        raise HTTPException(404, "Not found")
