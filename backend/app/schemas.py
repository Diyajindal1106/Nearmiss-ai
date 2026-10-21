import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from . import config


class ReportCreate(BaseModel):
    description: str = Field(min_length=10, max_length=1000)
    building: str
    location_details: Optional[str] = Field(default=None, max_length=200)
    category: str
    upload_id: Optional[str] = None

    @field_validator("description")
    @classmethod
    def _desc(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Description must be at least 10 characters.")
        return v

    @field_validator("building")
    @classmethod
    def _building(cls, v: str) -> str:
        if v not in config.BUILDINGS:
            raise ValueError("Unknown building/block.")
        return v

    @field_validator("category")
    @classmethod
    def _category(cls, v: str) -> str:
        if v not in config.CATEGORIES:
            raise ValueError("Unknown hazard category.")
        return v

    @field_validator("upload_id")
    @classmethod
    def _upload(cls, v):
        if v is not None and not re.fullmatch(r"[0-9a-f]{32}", v):
            raise ValueError("Invalid upload_id.")
        return v


class ReportUpdate(BaseModel):
    """Only fields present in the request body are changed."""

    category: Optional[str] = None
    status: Optional[str] = None
    priority_override: Optional[str] = None  # low|medium|high|urgent|auto
    severity: Optional[int] = Field(default=None, ge=1, le=5)
    assignee: Optional[str] = Field(default=None, max_length=120)
    resolution_notes: Optional[str] = Field(default=None, max_length=2000)
