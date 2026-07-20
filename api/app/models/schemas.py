"""Pydantic schemas + response envelope (plan Task 1.1 — BE foundation).

NOTE: Created by the AI lane to unblock the AI endpoints. This is BE-owned
foundation — Devik should reconcile/extend rather than recreate.
"""
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator

# Data-integrity guardrails (anti-fraud layer 1): reject physically-impossible
# inputs at the door so falsified numbers can't even enter as valid data. Plausible-
# but-suspicious values still pass here and are caught by the anomaly engine instead.
KNOWN_TESTS = {"malaria", "tb", "pregnancy", "diabetes", "hiv"}
MAX_DAILY_FOOTFALL = 10000  # generous cap to catch fat-finger typos, not real volume


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

    @model_validator(mode="after")
    def _occupied_within_total(self):
        if self.total is not None and self.occupied > self.total:
            raise ValueError("occupied beds cannot exceed total beds")
        return self


class FootfallLog(BaseModel):
    count: int = Field(ge=0, le=MAX_DAILY_FOOTFALL)
    opd: int = Field(ge=0, default=0)
    ipd: int = Field(ge=0, default=0)

    @model_validator(mode="after")
    def _breakdown_within_count(self):
        if self.opd + self.ipd > self.count:
            raise ValueError("opd + ipd cannot exceed total patient count")
        return self


class AttendanceLog(BaseModel):
    doctors_present: int = Field(ge=0)
    doctors_total: int = Field(gt=0)
    nurses_present: int = Field(ge=0, default=0)
    nurses_total: int = Field(ge=0, default=0)

    @model_validator(mode="after")
    def _present_within_total(self):
        if self.doctors_present > self.doctors_total:
            raise ValueError("doctors present cannot exceed total doctors")
        if self.nurses_present > self.nurses_total:
            raise ValueError("nurses present cannot exceed total nurses")
        return self


class TestsUpdate(BaseModel):
    tests: dict[str, bool]

    @model_validator(mode="after")
    def _known_tests_only(self):
        unknown = set(self.tests) - KNOWN_TESTS
        if unknown:
            raise ValueError(f"unknown test(s): {', '.join(sorted(unknown))}")
        return self


class CentreCreate(BaseModel):
    name: str = Field(min_length=1)
    type: Literal["PHC", "CHC"]
    block: str = Field(min_length=1)
    operator_email: str | None = None
    # "Roughly how many patients per day?" — drives cold-start stock levels
    expected_daily_patients: int | None = Field(default=None, ge=1, le=2000)
