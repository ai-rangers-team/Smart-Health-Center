"""Auth-guard tests (plan Task 1.2). These cover the Firestore-free paths — the
401 rejections and the role/centre guards — which run without live credentials.
The happy-path claim read (which calls verify_id_token) is exercised in integration.
"""
import pytest
from fastapi import HTTPException

from app import deps


def test_missing_token_401():
    with pytest.raises(HTTPException) as e:
        deps._user_from_token(None)
    assert e.value.status_code == 401


def test_malformed_header_401():
    with pytest.raises(HTTPException) as e:
        deps._user_from_token("Token abc")  # not "Bearer ..."
    assert e.value.status_code == 401


def test_require_role_rejects_wrong_role():
    guard = deps.require_role("district_admin")
    with pytest.raises(HTTPException) as e:
        guard({"role": "phc_operator"})
    assert e.value.status_code == 403


def test_require_role_allows_correct_role():
    guard = deps.require_role("district_admin")
    user = {"role": "district_admin", "uid": "u1"}
    assert guard(user) is user


def test_require_own_centre_rejects_other_centre():
    with pytest.raises(HTTPException) as e:
        deps.require_own_centre("phc_haveli", {"role": "phc_operator", "centre_id": "phc_mulshi"})
    assert e.value.status_code == 403


def test_require_own_centre_allows_own():
    # should not raise
    deps.require_own_centre("phc_mulshi", {"role": "phc_operator", "centre_id": "phc_mulshi"})
