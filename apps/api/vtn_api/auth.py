from __future__ import annotations

import base64
import hashlib
import hmac
import os

from fastapi import Cookie

from vtn_api.errors import ApiError

SESSION_COOKIE = "vtn_session"


def _cookie_secret() -> bytes:
    secret = os.environ.get("VTN_COOKIE_SECRET")
    if not secret:
        msg = "VTN_COOKIE_SECRET is required"
        raise RuntimeError(msg)
    return secret.encode()


def sign_session(username: str) -> str:
    payload = base64.urlsafe_b64encode(username.encode()).decode().rstrip("=")
    signature = hmac.new(_cookie_secret(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def verify_session(token: str) -> str | None:
    payload, separator, signature = token.partition(".")
    if not separator:
        return None

    expected = hmac.new(_cookie_secret(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None

    padding = "=" * (-len(payload) % 4)
    try:
        return base64.urlsafe_b64decode(f"{payload}{padding}").decode()
    except (UnicodeDecodeError, ValueError):
        return None


def require_session(vtn_session: str | None = Cookie(default=None)) -> str:
    if vtn_session is None:
        raise ApiError("unauthorized", "Missing session", 401)

    username = verify_session(vtn_session)
    if username is None:
        raise ApiError("unauthorized", "Invalid session", 401)
    return username
