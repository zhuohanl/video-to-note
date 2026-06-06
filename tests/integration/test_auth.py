from __future__ import annotations

import bcrypt
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from vtn_api.auth import require_session, sign_session
from vtn_api.errors import ApiError, api_error_handler
from vtn_api.routes.login import router as login_router


def _bcrypt_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()


def _app() -> FastAPI:
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(login_router)

    @app.get("/guarded")
    def guarded(session: str = Depends(require_session)) -> dict[str, str]:
        return {"session": session}

    return app


def test_login_sets_secure_http_only_session_cookie(monkeypatch) -> None:
    monkeypatch.setenv("VTN_USERNAME", "local")
    monkeypatch.setenv("VTN_PASSWORD_HASH", _bcrypt_hash("secret"))
    monkeypatch.setenv("VTN_COOKIE_SECRET", "test-cookie-secret")

    response = TestClient(_app()).post(
        "/login",
        json={"username": "local", "password": "secret"},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    set_cookie = response.headers["set-cookie"]
    assert "vtn_session=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "SameSite=lax" in set_cookie


def test_bad_login_returns_unauthorized_envelope(monkeypatch) -> None:
    monkeypatch.setenv("VTN_USERNAME", "local")
    monkeypatch.setenv("VTN_PASSWORD_HASH", _bcrypt_hash("secret"))
    monkeypatch.setenv("VTN_COOKIE_SECRET", "test-cookie-secret")

    response = TestClient(_app()).post(
        "/login",
        json={"username": "local", "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json() == {"error": {"code": "unauthorized", "message": "Invalid credentials"}}


def test_guarded_route_requires_valid_signed_cookie(monkeypatch) -> None:
    monkeypatch.setenv("VTN_COOKIE_SECRET", "test-cookie-secret")
    client = TestClient(_app())

    missing = client.get("/guarded")
    invalid = client.get("/guarded", headers={"cookie": "vtn_session=not-signed"})
    valid = client.get("/guarded", headers={"cookie": f"vtn_session={sign_session('local')}"})

    assert missing.status_code == 401
    assert missing.json() == {"error": {"code": "unauthorized", "message": "Missing session"}}
    assert invalid.status_code == 401
    assert invalid.json() == {"error": {"code": "unauthorized", "message": "Invalid session"}}
    assert valid.status_code == 200
    assert valid.json() == {"session": "local"}
