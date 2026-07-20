"""Data-integrity guardrails: physically-impossible operator inputs are rejected."""
import pytest
from pydantic import ValidationError

from app.models.schemas import AttendanceLog, BedsUpdate, FootfallLog, TestsUpdate


def test_beds_occupied_cannot_exceed_total():
    with pytest.raises(ValidationError):
        BedsUpdate(occupied=15, total=10)
    BedsUpdate(occupied=8, total=10)   # ok
    BedsUpdate(occupied=8)             # total omitted -> validated in endpoint, ok here


def test_attendance_present_cannot_exceed_total():
    with pytest.raises(ValidationError):
        AttendanceLog(doctors_present=3, doctors_total=2)
    with pytest.raises(ValidationError):
        AttendanceLog(doctors_present=1, doctors_total=2, nurses_present=5, nurses_total=3)
    AttendanceLog(doctors_present=2, doctors_total=2, nurses_present=3, nurses_total=3)  # ok


def test_footfall_breakdown_and_upper_bound():
    with pytest.raises(ValidationError):
        FootfallLog(count=10, opd=8, ipd=5)   # opd+ipd > count
    with pytest.raises(ValidationError):
        FootfallLog(count=99999)              # absurd (fat-finger) value
    FootfallLog(count=50, opd=40, ipd=10)     # ok


def test_tests_must_be_known():
    with pytest.raises(ValidationError):
        TestsUpdate(tests={"malaria": True, "covid": False})
    TestsUpdate(tests={"malaria": True, "tb": False, "pregnancy": True})  # ok
