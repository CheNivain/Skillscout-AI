"""Configuration and bounded public data contracts shared by the gateway and workers."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.0"
AGENTS = [
    ("profile", "Profile & training needs", 8101, "Identify professional skill gaps and a suitable learning direction."),
    ("trends", "Learning trend discovery", 8102, "Extract skills and learning signals from professional content."),
    ("retrieval", "Training opportunity retrieval", 8103, "Search the training catalogue with hybrid information retrieval."),
    ("recommendations", "Recommendation & notification", 8104, "Rank opportunities and explain their relevance."),
]


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def db_path() -> str:
    return os.environ.get("SKILLSCOUT_DB_PATH", str(ROOT / "data" / "skillscout.db"))


def agent_url(kind: str, port: int) -> str:
    return os.environ.get(f"{kind.upper()}_AGENT_URL", f"http://127.0.0.1:{port}").rstrip("/")


def agent_key() -> str:
    return os.environ.get("SKILLSCOUT_AGENT_KEY", "")


def scheduler_enabled() -> bool:
    return os.environ.get("SKILLSCOUT_SCHEDULER_ENABLED", "true").lower() == "true"


def scheduler_minutes() -> int:
    try:
        return max(1, min(10080, int(os.environ.get("SKILLSCOUT_SCHEDULER_MINUTES", "60"))))
    except ValueError:
        return 60


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


ShortText = Annotated[str, Field(min_length=1, max_length=120)]
SkillList = Annotated[list[ShortText], Field(max_length=80)]


class ProfileInput(StrictModel):
    user_id: str | None = Field(default=None, max_length=64)
    role_title: str = Field(default="", max_length=120)
    career_goal: str = Field(default="", max_length=160)
    experience_years: float = Field(default=0, ge=0, le=60)
    skills: SkillList = Field(default_factory=list)
    certifications: Annotated[list[Annotated[str, Field(min_length=1, max_length=240)]], Field(max_length=80)] = Field(default_factory=list)
    training_history: Annotated[list[Annotated[str, Field(min_length=1, max_length=240)]], Field(max_length=300)] = Field(default_factory=list)
    weekly_hours: float = Field(default=5, ge=0.5, le=60)
    budget: float = Field(default=100, ge=0, le=100000)
    interests: SkillList = Field(default_factory=list)
    bio: str = Field(default="", max_length=2000)
    notifications_enabled: bool = False
    consent: bool = False

    @field_validator("skills", "certifications", "training_history", "interests")
    @classmethod
    def unique_items(cls, values: list[str]) -> list[str]:
        seen: set[str] = set()
        return [value for value in values if not (value.casefold() in seen or seen.add(value.casefold()))]


def validate_https(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Provide an HTTPS source URL without embedded credentials")
    return value


class CourseInput(StrictModel):
    title: str = Field(min_length=3, max_length=240)
    provider: str = Field(min_length=1, max_length=120)
    url: str = Field(max_length=2000)
    description: str = Field(min_length=10, max_length=6000)
    skills: SkillList
    category: ShortText
    level: Literal["Beginner", "Intermediate", "Advanced"]
    duration_hours: float = Field(gt=0, le=5000)
    rating: float = Field(ge=0, le=5)
    price: float = Field(ge=0, le=100000)
    original_price: float = Field(ge=0, le=100000)
    currency: Literal["USD"] = "USD"
    discount_percent: float = Field(default=0, ge=0, le=100)
    offer_expires_at: str | None = None
    kind: Literal["Course", "Certification", "Learning path"]
    is_demo: bool
    source_note: str = Field(min_length=5, max_length=1000)

    @field_validator("url")
    @classmethod
    def https_url(cls, value: str) -> str:
        return validate_https(value)

    @field_validator("skills")
    @classmethod
    def course_skills(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("A course must identify at least one skill")
        return list(dict.fromkeys(value))

    @field_validator("offer_expires_at")
    @classmethod
    def valid_expiry(cls, value: str | None) -> str | None:
        if value is None:
            return None
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if date.tzinfo is None:
            raise ValueError("Offer expiry must include a timezone")
        return date.astimezone(timezone.utc).isoformat()

    @model_validator(mode="after")
    def coherent_price(self):
        if self.price > self.original_price:
            raise ValueError("Price cannot exceed original price")
        expected = round((1 - self.price / self.original_price) * 100, 1) if self.original_price else 0
        if abs(self.discount_percent - expected) > 1:
            raise ValueError("Discount must match the original and current prices")
        if self.discount_percent > 0 and not self.offer_expires_at:
            raise ValueError("Discounted courses need an offer expiry")
        return self


class PostInput(StrictModel):
    text: str = Field(min_length=10, max_length=10000)
    source: str = Field(min_length=1, max_length=200)
    source_url: str | None = Field(default=None, max_length=2000)
    published_at: str = Field(default_factory=utcnow)
    is_demo: bool

    @field_validator("source_url")
    @classmethod
    def https_url(cls, value: str | None) -> str | None:
        return validate_https(value) if value else None

    @field_validator("published_at")
    @classmethod
    def valid_published(cls, value: str) -> str:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if date.tzinfo is None:
            raise ValueError("Published date must include a timezone")
        if date > datetime.now(timezone.utc):
            raise ValueError("Published date cannot be in the future")
        return date.astimezone(timezone.utc).isoformat()
