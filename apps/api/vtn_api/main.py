from typing import Any, cast

from fastapi import FastAPI

from vtn_api.errors import ApiError, api_error_handler
from vtn_api.routes.login import router as login_router

app = FastAPI(title="Video-to-Note API")
app.add_exception_handler(ApiError, cast(Any, api_error_handler))
app.include_router(login_router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
