"""Authenticated operator API and same-origin review console."""
from __future__ import annotations

import hmac
import json
import logging
import time
from importlib.resources import files
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from mdm.config import Actor, actors
from mdm.domain import SourceRecord
from mdm.service import Conflict, Service

logger = logging.getLogger("mdm.requests")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False
bearer = HTTPBearer(auto_error=False)


class BodyLimitMiddleware:
    """Bound actual bytes even when a client omits Content-Length."""

    def __init__(self, app, max_bytes=10_000_000):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            return await self.app(scope, receive, send)
        messages, size = [], 0
        while True:
            message = await receive()
            size += len(message.get("body", b""))
            if size > self.max_bytes:
                return await JSONResponse({"detail": "request body exceeds configured byte limit"}, 413)(scope, receive, send)
            messages.append(message)
            if not message.get("more_body", False):
                break
        async def replay():
            if messages:
                return messages.pop(0)
            return await receive()
        return await self.app(scope, replay, send)


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MergeInput(StrictInput):
    group_ids: list[str] = Field(min_length=2, max_length=20)
    expected_versions: dict[str, int]
    reason: str = Field(min_length=1, max_length=2000)
    idempotency_key: str = Field(min_length=1, max_length=160)


class PreviewInput(StrictInput):
    group_ids: list[str] = Field(min_length=2, max_length=20)


class SplitInput(StrictInput):
    group_id: str
    partitions: list[list[str]] = Field(min_length=2, max_length=20)
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=2000)
    idempotency_key: str = Field(min_length=1, max_length=160)


class UnmergeInput(StrictInput):
    merge_decision_id: str
    expected_versions: dict[str, int]
    reason: str = Field(min_length=1, max_length=2000)
    idempotency_key: str = Field(min_length=1, max_length=160)


class VersionInput(StrictInput):
    expected_version: int = Field(ge=1)


class IngestInput(StrictInput):
    records: list[SourceRecord] = Field(max_length=10000)


def create_app(service: Service | None = None, actor_map: dict[str, Actor] | None = None, *, body_limit: int = 10_000_000) -> FastAPI:
    app = FastAPI(title="Enterprise Master Data Reconciliation", version="0.1.0rc1",
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(BodyLimitMiddleware, max_bytes=body_limit)

    def svc() -> Service:
        nonlocal service
        if service is None:
            service = Service()
        return service

    def principal(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Actor:
        nonlocal actor_map
        if actor_map is None:
            actor_map = actors()
        if credentials is not None:
            for token, actor in actor_map.items():
                if hmac.compare_digest(token.encode(), credentials.credentials.encode()):
                    return actor
        raise HTTPException(401, "A configured bearer token is required", headers={"WWW-Authenticate": "Bearer"})

    @app.middleware("http")
    async def observe(request: Request, call_next):
        correlation = str(uuid4())
        started = time.monotonic()
        length = request.headers.get("content-length", "0")
        try:
            too_large = int(length) > 10_000_000
        except ValueError:
            return JSONResponse({"detail": "invalid content length"}, 400)
        if too_large:
            return JSONResponse({"detail": "request body exceeds 10 MB"}, 413)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        logger.info(json.dumps({"event": "http.request", "correlation_id": correlation, "method": request.method,
                                "route": request.scope.get("route").path if request.scope.get("route") else "unmatched",
                                "status": response.status_code, "duration_ms": round((time.monotonic()-started)*1000, 2)}))
        return response

    @app.exception_handler(Conflict)
    async def conflict_handler(request, exc):
        return JSONResponse({"detail": str(exc)}, 409)

    @app.exception_handler(PermissionError)
    async def forbidden_handler(request, exc):
        return JSONResponse({"detail": str(exc)}, 403)

    @app.exception_handler(ValueError)
    async def invalid_handler(request, exc):
        return JSONResponse({"detail": str(exc)}, 422)

    @app.exception_handler(KeyError)
    async def not_found_handler(request, exc):
        return JSONResponse({"detail": "record not found"}, 404)

    @app.get("/", response_class=HTMLResponse)
    def console():
        return files("mdm").joinpath("static/index.html").read_text()

    @app.get("/assets/app.js")
    def javascript():
        return PlainTextResponse(files("mdm").joinpath("static/app.js").read_text(), media_type="text/javascript")

    @app.get("/assets/style.css")
    def styles():
        return PlainTextResponse(files("mdm").joinpath("static/style.css").read_text(), media_type="text/css")

    @app.get("/healthz")
    def health():
        try:
            with svc().db.connect() as conn:
                if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=1").fetchone():
                    return JSONResponse({"status": "unavailable"}, 503)
            return {"status": "ok"}
        except Exception:
            return JSONResponse({"status": "unavailable"}, 503)

    @app.get("/api/me")
    def me(actor=Depends(principal)):
        return {"name": actor.name, "role": actor.role}

    @app.get("/api/overview")
    def overview(actor=Depends(principal)):
        return {"snapshot": svc().snapshot(), "quality": svc().quality()}

    @app.get("/api/golden/{golden_id}/history")
    def history(golden_id: str, actor=Depends(principal)):
        return svc().history(golden_id)

    @app.get("/api/openapi.json")
    def openapi(actor=Depends(principal)):
        return app.openapi()

    @app.get("/metrics")
    def metrics(actor=Depends(principal)):
        quality = svc().quality()
        rows = [f"mdm_{key} {value}" for key, value in quality.items() if isinstance(value, (int, float))]
        return PlainTextResponse("\n".join(rows)+"\n")

    @app.post("/api/ingest")
    def ingest(body: IngestInput, actor=Depends(principal)):
        actor.require("executor")
        return svc().ingest(body.records)

    @app.post("/api/reconcile")
    def reconcile(actor=Depends(principal)):
        actor.require("executor")
        return svc().reconcile()

    @app.post("/api/consume")
    def consume(actor=Depends(principal)):
        actor.require("executor")
        return svc().consume()

    @app.post("/api/decisions/merge", status_code=201)
    def merge(body: MergeInput, actor=Depends(principal)):
        return svc().request_merge(**body.model_dump(), actor=actor)

    @app.post("/api/preview-merge")
    def preview(body: PreviewInput, actor=Depends(principal)):
        return svc().preview_merge(body.group_ids)

    @app.post("/api/decisions/split", status_code=201)
    def split(body: SplitInput, actor=Depends(principal)):
        return svc().request_split(**body.model_dump(), actor=actor)

    @app.post("/api/decisions/unmerge", status_code=201)
    def unmerge(body: UnmergeInput, actor=Depends(principal)):
        return svc().request_unmerge(**body.model_dump(), actor=actor)

    @app.post("/api/decisions/{decision_id}/approve")
    def approve(decision_id: str, body: VersionInput, actor=Depends(principal)):
        return svc().approve(decision_id, actor, body.expected_version)

    @app.post("/api/decisions/{decision_id}/reject")
    def reject(decision_id: str, body: VersionInput, actor=Depends(principal)):
        return svc().approve(decision_id, actor, body.expected_version, reject=True)

    @app.post("/api/decisions/{decision_id}/execute")
    def execute(decision_id: str, body: VersionInput, actor=Depends(principal)):
        return svc().execute(decision_id, actor, body.expected_version)

    return app


app = create_app()
