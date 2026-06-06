from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

ERROR_CODES = {
    "unsupported_url",
    "video_unavailable",
    "transcript_failed",
    "job_not_review_ready",
    "needs_ack",
    "stale_write",
    "version_not_found",
    "unauthorized",
    "validation_error",
}


class ApiError(Exception):
    def __init__(self, code: str, message: str, http_status: int) -> None:
        if code not in ERROR_CODES:
            msg = f"unknown API error code: {code}"
            raise ValueError(msg)
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)

    def envelope(self) -> dict[str, dict[str, str]]:
        return {"error": {"code": self.code, "message": self.message}}


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    del request
    return JSONResponse(status_code=exc.http_status, content=exc.envelope())
