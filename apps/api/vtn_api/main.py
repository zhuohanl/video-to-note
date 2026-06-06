from typing import Any, cast

from fastapi import FastAPI

from vtn_api.errors import ApiError, api_error_handler
from vtn_api.routes.clips import router as clips_router
from vtn_api.routes.export import router as export_router
from vtn_api.routes.jobs import router as jobs_router
from vtn_api.routes.login import router as login_router
from vtn_api.routes.media import router as media_router
from vtn_api.routes.note import router as note_router
from vtn_api.routes.versions import router as versions_router
from vtn_api.sse import router as sse_router

app = FastAPI(title="Video-to-Note API")
app.add_exception_handler(ApiError, cast(Any, api_error_handler))
app.include_router(login_router)
app.include_router(jobs_router)
app.include_router(clips_router)
app.include_router(export_router)
app.include_router(media_router)
app.include_router(note_router)
app.include_router(versions_router)
app.include_router(sse_router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
