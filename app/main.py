import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.config import settings

log = logging.getLogger("haru.startup")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Load the seeded lessons (app/seed/lessons) into the database. Idempotent: an
    unchanged lesson costs one SELECT. A problem here is logged and the API starts
    anyway — the lessons already in the database keep working."""
    from app.services import lesson_seed

    try:
        report = await asyncio.to_thread(lesson_seed.run_startup_sync)
        if report:
            log.warning("[lesson_seed] %s", ", ".join(f"{slug}={state}" for slug, state in report.items()))
    except Exception:  # noqa: BLE001 - never keep the API from starting over lesson data
        log.exception("[lesson_seed] could not load the seeded lessons")
    yield


app = FastAPI(
    title="Haru API",
    version="0.1.0",
    description="Backend for the Haru Korean-learning app (FastAPI + Celery + Redis + Postgres/pgvector).",
    lifespan=lifespan,
)

# CORS: the Lovable frontend is a separate origin; no cookies, Bearer-JWT
# only, so allow_credentials stays False. cors_origin_list covers exact
# known origins (published domain); the regex covers Lovable's rotating
# id-preview-*.lovable.app subdomains without needing a redeploy per preview.
@app.middleware("http")
async def unhandled_to_problem_json(request: Request, call_next):
    """An unhandled error would otherwise come out of Starlette's outermost layer as a bare 500
    WITHOUT the CORS headers, which a browser reports as "blocked by CORS policy" and hides the
    real failure. This layer sits inside CORSMiddleware (added below, so it wraps this one): the
    500 is logged here and returned as problem+json with the CORS headers the browser needs."""
    try:
        return await call_next(request)
    except Exception:  # noqa: BLE001 - last line of defence, the error is logged with its traceback
        logging.getLogger("haru.api").exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"type": "about:blank", "title": "Lỗi máy chủ", "status": 500},
            media_type="application/problem+json",
        )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def problem_json_handler(request: Request, exc: StarletteHTTPException):
    """Normalizes every HTTPException into RFC 9457 problem+json, per
    SDD §7. `detail` is either already a problem dict (raised via
    app.api.deps._problem) or a plain string (framework-raised errors)."""
    body = exc.detail
    if not isinstance(body, dict):
        body = {"type": "about:blank", "title": str(body), "status": exc.status_code}
    return JSONResponse(
        status_code=exc.status_code,
        content=body,
        media_type="application/problem+json",
        headers=getattr(exc, "headers", None),  # Retry-After on a 429, WWW-Authenticate on a 401
    )


@app.get("/healthz", tags=["ops"])
async def healthz():
    return {"status": "ok", "environment": settings.ENVIRONMENT}


app.include_router(api_router)
