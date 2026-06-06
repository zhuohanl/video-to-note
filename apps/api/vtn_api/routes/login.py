from __future__ import annotations

import os

import bcrypt
from fastapi import APIRouter, Response

from vtn_api.auth import SESSION_COOKIE, sign_session
from vtn_api.errors import ApiError
from vtn_api.schemas import LoginBody

router = APIRouter()


def _expected_username() -> str:
    return os.environ.get("VTN_USERNAME", "local")


def _password_hash() -> bytes:
    value = os.environ.get("VTN_PASSWORD_HASH")
    if not value:
        msg = "VTN_PASSWORD_HASH is required"
        raise RuntimeError(msg)
    return value.encode()


@router.post("/login")
def login(body: LoginBody, response: Response) -> dict[str, bool]:
    password_ok = bcrypt.checkpw(body.password.encode(), _password_hash())
    if body.username != _expected_username() or not password_ok:
        raise ApiError("unauthorized", "Invalid credentials", 401)

    response.set_cookie(
        SESSION_COOKIE,
        sign_session(body.username),
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return {"ok": True}
