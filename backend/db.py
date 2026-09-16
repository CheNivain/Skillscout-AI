"""Small SQLite repository. Each operation owns its connection and transaction."""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from backend import config
from backend.security import hash_password


def dump(value) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


@contextmanager
def connection():
    conn = sqlite3.connect(config.db_path(), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize() -> None:
    location = Path(config.db_path())
    location.parent.mkdir(parents=True, exist_ok=True)
    with connection() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('employee','hr','admin')),
            password_hash TEXT NOT NULL, profile_json TEXT NOT NULL,
            profile_version INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            csrf_token TEXT NOT NULL, expires_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS courses (id TEXT PRIMARY KEY, data_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS posts (id TEXT PRIMARY KEY, data_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            data_json TEXT NOT NULL, started_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS runs_user_date ON runs(user_id, started_at DESC);
        CREATE TABLE IF NOT EXISTS analyses (
            user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            profile_version INTEGER NOT NULL, data_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS learning_plan (
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            course_id TEXT NOT NULL REFERENCES courses(id), status TEXT NOT NULL,
            saved_at TEXT NOT NULL, completed_at TEXT,
            PRIMARY KEY(user_id, course_id)
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            data_json TEXT NOT NULL, dedupe_key TEXT NOT NULL, created_at TEXT NOT NULL,
            UNIQUE(user_id, dedupe_key)
        );
        """)
        # A killed process must not leave a permanently running trace.
        for row in conn.execute("SELECT id,data_json FROM runs"):
            run = json.loads(row["data_json"])
            if run["status"] == "running":
                run.update(status="failed", finished_at=config.utcnow(), error="The service restarted before this run finished. Please try again.")
                for step in run["steps"]:
                    if step["status"] == "running":
                        step.update(status="failed", error=run["error"])
                conn.execute("UPDATE runs SET data_json=? WHERE id=?", (dump(run), row["id"]))
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (config.utcnow(),))
    try:
        os.chmod(location, 0o600)
    except OSError:
        pass
    seed()


def default_profile(user_id: str) -> dict:
    return config.ProfileInput(user_id=user_id).model_dump()


def seed() -> None:
    from backend.data.seed import get_seed_courses, get_seed_posts

    with connection() as conn:
        if not conn.execute("SELECT 1 FROM courses LIMIT 1").fetchone():
            conn.executemany("INSERT INTO courses VALUES (?,?)", [(item["id"], dump(item)) for item in get_seed_courses()])
        if not conn.execute("SELECT 1 FROM posts LIMIT 1").fetchone():
            conn.executemany("INSERT INTO posts VALUES (?,?)", [(item["id"], dump(item)) for item in get_seed_posts()])
        if os.environ.get("SKILLSCOUT_SEED_DEMO", "true").lower() != "true":
            return
        # Seed once, not on every startup: users can delete their demo accounts.
        conn.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        if conn.execute("SELECT 1 FROM metadata WHERE key='demo_seeded'").fetchone():
            return
        password_hash = hash_password("SkillScout123!")
        for name, email, role in [("Alex Morgan", "alex@skillscout.demo", "employee"), ("Jordan Lee", "hr@skillscout.demo", "hr"), ("Sam Taylor", "admin@skillscout.demo", "admin")]:
            uid = str(uuid4())
            profile = default_profile(uid)
            if role == "employee":
                profile.update(role_title="Data Analyst", career_goal="Data Scientist", experience_years=3,
                               skills=["SQL", "Excel", "Power BI"], weekly_hours=6, budget=80,
                               interests=["Data Science", "Artificial Intelligence"], consent=True,
                               notifications_enabled=True, bio="Turn business insights into intelligent products.")
            else:
                profile.update(role_title="Learning & Development Manager" if role == "hr" else "Platform Administrator")
            conn.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?,?,1,?)", (uid, name, email, role, password_hash, dump(profile), config.utcnow()))
        conn.execute("INSERT INTO metadata VALUES ('demo_seeded','true')")


def user_by_id(uid: str) -> dict | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        return dict(row) if row else None


def user_by_email(email: str) -> dict | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE email=?", (email.casefold(),)).fetchone()
        return dict(row) if row else None


def public_user(user: dict) -> dict:
    return {key: user[key] for key in ("id", "name", "email", "role")}


def profile(user: dict) -> dict:
    return json.loads(user["profile_json"])


def create_user(name: str, email: str, password: str) -> dict:
    uid = str(uuid4())
    encoded = hash_password(password)
    with connection() as conn:
        conn.execute("INSERT INTO users VALUES (?,?,?,?,?,?,1,?)", (uid, name, email.casefold(), "employee", encoded, dump(default_profile(uid)), config.utcnow()))
    return user_by_id(uid)


def save_profile(uid: str, value: dict, conn=None) -> None:
    if conn is None:
        with connection() as own_conn:
            save_profile(uid, value, own_conn)
        return
    value = {**value, "user_id": uid}
    conn.execute("UPDATE users SET profile_json=?,profile_version=profile_version+1 WHERE id=?", (dump(value), uid))
    conn.execute("DELETE FROM analyses WHERE user_id=?", (uid,))
    # Recommendations and opportunity alerts refer to the old profile.
    conn.execute("DELETE FROM notifications WHERE user_id=?", (uid,))


def session_create(uid: str, token_hash: str, csrf: str) -> None:
    expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    with connection() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (config.utcnow(),))
        conn.execute("INSERT INTO sessions VALUES (?,?,?,?)", (token_hash, uid, csrf, expires))


def session_get(token_hash: str) -> dict | None:
    with connection() as conn:
        row = conn.execute("SELECT sessions.csrf_token,users.* FROM sessions JOIN users ON sessions.user_id=users.id WHERE token_hash=? AND expires_at>?", (token_hash, config.utcnow())).fetchone()
        return dict(row) if row else None


def session_delete(token_hash: str) -> None:
    with connection() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash,))


def items(table: str) -> list[dict]:
    assert table in ("courses", "posts")
    with connection() as conn:
        result = [json.loads(row[0]) for row in conn.execute(f"SELECT data_json FROM {table} ORDER BY rowid")]
    return [_public_course(course) for course in result] if table == "courses" else result


def item(table: str, identifier: str) -> dict | None:
    assert table in ("courses", "posts")
    with connection() as conn:
        row = conn.execute(f"SELECT data_json FROM {table} WHERE id=?", (identifier,)).fetchone()
        value = json.loads(row[0]) if row else None
    return _public_course(value) if value and table == "courses" else value


def _public_course(course: dict) -> dict:
    from backend.ai.engine import effective_course
    return effective_course(course)


def add_item(table: str, value: dict) -> dict:
    assert table in ("courses", "posts")
    with connection() as conn:
        conn.execute(f"INSERT INTO {table} VALUES (?,?)", (value["id"], dump(value)))
        # A fresh source warrants a fresh retrieval on the next run.
    return value


def save_run(uid: str, run: dict) -> None:
    with connection() as conn:
        if conn.execute("SELECT 1 FROM users WHERE id=?", (uid,)).fetchone():
            conn.execute("INSERT INTO runs VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET data_json=excluded.data_json", (run["id"], uid, dump(run), run["started_at"]))


def runs(uid: str, limit: int | None = 20) -> list[dict]:
    with connection() as conn:
        return [json.loads(row[0]) for row in conn.execute("SELECT data_json FROM runs WHERE user_id=? ORDER BY started_at DESC LIMIT ?", (uid, limit if limit is not None else -1))]


def get_run(uid: str, rid: str) -> dict | None:
    with connection() as conn:
        row = conn.execute("SELECT data_json FROM runs WHERE id=? AND user_id=?", (rid, uid)).fetchone()
        return json.loads(row[0]) if row else None


def analysis(uid: str) -> dict:
    with connection() as conn:
        row = conn.execute("SELECT analyses.data_json FROM analyses JOIN users ON users.id=analyses.user_id AND users.profile_version=analyses.profile_version WHERE user_id=?", (uid,)).fetchone()
        result = json.loads(row[0]) if row else {"needs": None, "trends": [], "recommendations": []}
    recommendations = result.get("recommendations", [])
    if any(_public_course(rec["course"]) != rec["course"] for rec in recommendations):
        # Reprice and rescore persisted results as offers expire, including the
        # explanation. Merely replacing the displayed price leaves a stale claim.
        from backend.ai.engine import recommend
        employee = user_by_id(uid)
        if employee and result.get("needs"):
            refreshed = recommend(profile(employee), result["needs"], result.get("trends", []), recommendations)
            dates = {rec["id"]: rec["generated_at"] for rec in recommendations}
            for rec in refreshed:
                rec["generated_at"] = dates.get(rec["id"], rec["generated_at"])
            result["recommendations"] = refreshed
    return result


def commit_analysis(uid: str, version: int, result: dict, notices: list[dict]) -> bool:
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT profile_version,profile_json FROM users WHERE id=?", (uid,)).fetchone()
        if not row or row["profile_version"] != version or not json.loads(row["profile_json"])["consent"]:
            return False
        conn.execute("INSERT INTO analyses VALUES (?,?,?) ON CONFLICT(user_id) DO UPDATE SET profile_version=excluded.profile_version,data_json=excluded.data_json", (uid, version, dump(result)))
        if json.loads(row["profile_json"])["notifications_enabled"]:
            for notice in notices:
                key = notice["dedupe_key"]
                public_notice = {key: value for key, value in notice.items() if key != "dedupe_key"}
                conn.execute("INSERT OR IGNORE INTO notifications VALUES (?,?,?,?,?)", (notice["id"], uid, dump(public_notice), key, notice["created_at"]))
    return True


def notifications(uid: str, limit: int | None = 200) -> list[dict]:
    with connection() as conn:
        notices = [json.loads(row[0]) for row in conn.execute("SELECT data_json FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (uid, limit if limit is not None else -1))]
    for notice in notices:
        course = item("courses", notice.get("course_id")) if notice.get("course_id") else None
        if course and course.get("offer_expired"):
            notice["title"] = "Learning opportunity · offer expired"
            notice["message"] = (f"The offer recorded for {course['title']} has expired. "
                                 f"The catalogue now lists USD {course['price']:g}. "
                                 "Check the provider for current details and run discovery for an updated match.")
    return notices


def mark_read(uid: str, nid: str) -> bool:
    with connection() as conn:
        if nid == "all":
            rows = conn.execute("SELECT id,data_json FROM notifications WHERE user_id=?", (uid,)).fetchall()
        else:
            rows = conn.execute("SELECT id,data_json FROM notifications WHERE user_id=? AND id=?", (uid, nid)).fetchall()
        for row in rows:
            value = json.loads(row["data_json"])
            value["read"] = True
            conn.execute("UPDATE notifications SET data_json=? WHERE id=?", (dump(value), row["id"]))
        return bool(rows) or nid == "all"


def plan(uid: str) -> list[dict]:
    with connection() as conn:
        return [dict(course=_public_course(json.loads(row["data_json"])), status=row["status"], saved_at=row["saved_at"], completed_at=row["completed_at"]) for row in conn.execute("SELECT learning_plan.*,courses.data_json FROM learning_plan JOIN courses ON courses.id=course_id WHERE user_id=? ORDER BY saved_at DESC", (uid,))]


def save_plan(uid: str, course: dict, status: str) -> dict:
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute("SELECT * FROM learning_plan WHERE user_id=? AND course_id=?", (uid, course["id"])).fetchone()
        saved_at = existing["saved_at"] if existing else config.utcnow()
        completed_at = ((existing["completed_at"] if existing else None) or config.utcnow()) if status == "completed" else None
        conn.execute("INSERT INTO learning_plan VALUES (?,?,?,?,?) ON CONFLICT(user_id,course_id) DO UPDATE SET status=excluded.status,completed_at=excluded.completed_at", (uid, course["id"], status, saved_at, completed_at))
        if status == "completed" and (not existing or existing["status"] != "completed"):
            row = conn.execute("SELECT profile_json FROM users WHERE id=?", (uid,)).fetchone()
            value = json.loads(row[0])
            for field, additions in [("training_history", [course["title"]]), ("skills", course["skills"]), ("certifications", [course["title"]] if course["kind"] == "Certification" else [])]:
                present = {x.casefold() for x in value[field]}
                for addition in additions:
                    if addition.casefold() not in present:
                        value[field].append(addition)
                        present.add(addition.casefold())
            # Keep automatic completion feedback within the same contract as editable profiles.
            config.ProfileInput.model_validate(value)
            save_profile(uid, value, conn)
    return dict(course=course, status=status, saved_at=saved_at, completed_at=completed_at)


def delete_plan(uid: str, cid: str) -> None:
    with connection() as conn:
        conn.execute("DELETE FROM learning_plan WHERE user_id=? AND course_id=?", (uid, cid))


def delete_user(uid: str) -> bool:
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT role FROM users WHERE id=?", (uid,)).fetchone()
        if row and row["role"] == "admin" and conn.execute("SELECT count(*) FROM users WHERE role='admin'").fetchone()[0] <= 1:
            return False
        conn.execute("DELETE FROM users WHERE id=?", (uid,))
    return True


def all_users() -> list[dict]:
    with connection() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM users")]
