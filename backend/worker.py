"""One independently launched authenticated HTTP service for each specialized agent."""
from __future__ import annotations

import asyncio
import hmac
import json
import logging
import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import Field, ValidationError, field_validator

from backend import config
from backend.security import BodyLimitMiddleware

logger = logging.getLogger(__name__)
app = FastAPI(title="SkillScout agent worker", docs_url=None, redoc_url=None, openapi_url=None)


class Envelope(config.StrictModel):
    run_id: str = Field(min_length=1, max_length=64)
    user_id: str = Field(min_length=1, max_length=64)
    payload: dict[str, Any]

    @field_validator("payload")
    @classmethod
    def bound_payload(cls, value):
        def check(node, depth=0):
            if depth > 12:
                raise ValueError("Payload nesting is too deep")
            if isinstance(node, dict):
                if len(node) > 100:
                    raise ValueError("Too many object fields")
                for key, child in node.items():
                    if len(key) > 120:
                        raise ValueError("Field name too long")
                    check(child, depth + 1)
            elif isinstance(node, list):
                if len(node) > 2000:
                    raise ValueError("Too many input items")
                for child in node:
                    check(child, depth + 1)
            elif isinstance(node, str) and len(node) > 20000:
                raise ValueError("Input text is too long")
        check(value)
        if len(json.dumps(value, allow_nan=False)) > 2_000_000:
            raise ValueError("Payload is too large")
        return value


app.add_middleware(BodyLimitMiddleware, limit=2_100_000)


@app.get("/health")
def health():
    return {"status": "ok" if config.agent_key() else "unconfigured", "kind": os.environ.get("AGENT_KIND", "profile")}


def validated_payload(kind: str, payload: dict) -> dict:
    required = {"profile": {"profile"}, "trends": {"posts", "needs"},
                "retrieval": {"courses", "needs", "trends"},
                "recommendations": {"profile", "needs", "trends", "candidates"}}
    if kind not in required:
        raise ValueError("Unknown agent kind")
    if set(payload) != required[kind]:
        raise ValueError("The payload does not match this agent's input contract")
    if "profile" in payload:
        payload["profile"] = config.ProfileInput.model_validate(payload["profile"]).model_dump()
    for field in ("posts", "courses", "trends", "candidates"):
        if field in payload and (not isinstance(payload[field], list) or any(not isinstance(x, dict) for x in payload[field])):
            raise ValueError(f"{field} must be a list of objects")
    if "needs" in payload:
        needs = payload["needs"]
        if not isinstance(needs, dict) or not all(isinstance(needs.get(key), list) and all(isinstance(x, str) for x in needs[key]) for key in ("current_skills", "target_skills", "skill_gaps", "priority_skills")):
            raise ValueError("Needs must include valid skill lists")
    if "posts" in payload:
        for post in payload["posts"]:
            if not isinstance(post.get("text"), str) or not isinstance(post.get("published_at"), str):
                raise ValueError("Post text and publication date are required")
    for course in payload.get("courses", []) + [item.get("course", {}) for item in payload.get("candidates", [])]:
        if not all(isinstance(course.get(key), str) for key in ("id", "title", "provider", "url")) or not isinstance(course.get("skills"), list):
            raise ValueError("Each course must contain its identifier, title, provider, URL and skills")
    return payload


@app.post("/execute")
async def execute(envelope: Envelope, x_agent_key: str | None = Header(default=None)):
    secret = config.agent_key()
    if not secret or not x_agent_key or not hmac.compare_digest(secret, x_agent_key):
        raise HTTPException(status_code=401, detail="Invalid agent credentials")
    kind = os.environ.get("AGENT_KIND", "profile")
    try:
        payload = validated_payload(kind, envelope.payload)
        if "profile" in payload and payload["profile"].get("user_id") != envelope.user_id:
            raise ValueError("Profile and envelope employee identifiers must match")
        if "profile" in payload and not payload["profile"].get("consent"):
            raise ValueError("Profile consent is required")
    except (ValueError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail="Invalid agent payload: " + str(exc)[:240]) from None
    from backend.ai import engine
    handlers = {"profile": engine.analyze_profile, "trends": engine.discover_trends,
                "retrieval": engine.retrieve_courses, "recommendations": engine.recommend}
    try:
        result = await asyncio.to_thread(handlers[kind], **payload)
    except Exception:
        logger.exception("Agent %s failed in run %s", kind, envelope.run_id)
        raise HTTPException(status_code=500, detail=f"The {kind} agent could not complete this request") from None
    return {"run_id": envelope.run_id, "agent": kind, "result": result}
