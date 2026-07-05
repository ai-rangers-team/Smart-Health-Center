"""Pydantic schemas + response envelope (plan Task 1.1 — BE foundation).

NOTE: Created by the AI lane to unblock the AI endpoints. This is BE-owned
foundation — Devik should reconcile/extend rather than recreate.
"""
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def ok(data):
    return {"success": True, "data": data, "timestamp": datetime.now(timezone.utc).isoformat()}


def err(message: str, code: int):
    return {"success": False, "error": message, "code": code}


class StockUpdate(BaseModel):
    medicine_id: str
    current_stock: float = Field(ge=0)


class BedsUpdate(BaseModel):
    occupied: int = Field(ge=0)
    total: int | None = Field(default=None, ge=0)


class FootfallLog(BaseModel):
    count: int = Field(ge=0)
    opd: int = Field(ge=0, default=0)
    ipd: int = Field(ge=0, default=0)


class AttendanceLog(BaseModel):
    doctors_present: int = Field(ge=0)
    doctors_total: int = Field(gt=0)
    nurses_present: int = Field(ge=0, default=0)
    nurses_total: int = Field(ge=0, default=0)


class TestsUpdate(BaseModel):
    tests: dict[str, bool]


class CentreCreate(BaseModel):
    name: str = Field(min_length=1)
    type: Literal["PHC", "CHC"]
    block: str = Field(min_length=1)
    operator_email: str | None = None
    # "Roughly how many patients per day?" — drives cold-start stock levels
    expected_daily_patients: int | None = Field(default=None, ge=1, le=2000)
