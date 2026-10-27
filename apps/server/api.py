"""현재 OS 사용자용 로컬 API. 원격 서버로 노출하지 않는다."""

from __future__ import annotations

import base64
import secrets
from pathlib import Path
from typing import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger

from packages.core import Core
from packages.platform.domain import DomainError, Json, fields, text
from packages.platform.storage import EncryptedStore

#: 저장소 탐색 대신 명시적으로 허용한 웹 자산만 제공한다.
WEB_ROOT = Path(__file__).resolve().parents[1] / "web"
ASSETS = {
    "": ("index.html", "text/html"),
    "index.html": ("index.html", "text/html"),
    "app.js": ("app.js", "text/javascript"),
    "report.js": ("report.js", "text/javascript"),
    "styles.css": ("styles.css", "text/css"),
    "report.css": ("report.css", "text/css"),
    "functional.css": ("functional.css", "text/css"),
    "favicon.svg": ("favicon.svg", "image/svg+xml"),
}
#: 5MB 증빙의 base64 표현과 JSON 헤더를 포함하는 요청 상한.
MAX_BODY_BYTES = 8 * 1024 * 1024


def create_app(store: EncryptedStore, demo: bool = False, port: int = 4173) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    core = Core(store)
    session = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    bootstrap = secrets.token_urlsafe(32)
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    app.state.core = core
    app.state.bootstrap = bootstrap

    @app.middleware("http")
    async def protect(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        host = request.headers.get("host", "")
        if host not in hosts:
            return JSONResponse(
                {"error": "허용되지 않은 로컬 호스트입니다."}, status_code=400
            )
        if request.url.path.startswith("/api/"):
            login = request.url.path == "/api/session" and request.method == "POST"
            cookie = request.cookies.get("whoiam_session", "")
            if not login and not secrets.compare_digest(cookie, session):
                return JSONResponse(
                    {"error": "로컬 화면을 다시 열어주세요."}, status_code=401
                )
            if request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse(
                    {"error": "외부 사이트 요청은 허용하지 않습니다."}, status_code=403
                )
            if request.method != "GET":
                if request.headers.get("origin") != f"http://{host}" or (
                    not login
                    and not secrets.compare_digest(
                        request.headers.get("x-whoiam-csrf", ""), csrf
                    )
                ):
                    return JSONResponse(
                        {"error": "요청 출처를 확인해주세요."}, status_code=403
                    )
                if (
                    request.headers.get("content-type", "").split(";")[0]
                    != "application/json"
                ):
                    return JSONResponse(
                        {"error": "JSON 요청만 허용합니다."}, status_code=415
                    )
                try:
                    length = int(request.headers.get("content-length", "-1"))
                except ValueError:
                    length = -1
                if length < 0 or request.headers.get("transfer-encoding"):
                    return JSONResponse(
                        {"error": "요청 크기를 확인해주세요."}, status_code=411
                    )
                if length > MAX_BODY_BYTES:
                    return JSONResponse(
                        {"error": "요청 파일이 너무 큽니다."}, status_code=413
                    )
        try:
            response = await call_next(request)
        except Exception:
            logger.error("Local request failed; request details omitted")
            response = JSONResponse(
                {"error": "처리하지 못했습니다. 입력과 저장소 상태를 확인해주세요."},
                status_code=500,
            )
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
                "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
            }
        )
        return response

    @app.exception_handler(DomainError)
    async def domain_error(request: Request, error: DomainError) -> JSONResponse:
        return JSONResponse({"error": str(error)}, status_code=error.status)

    @app.exception_handler(RequestValidationError)
    async def invalid_input(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse({"error": "입력값의 형식을 확인해주세요."}, status_code=422)

    @app.get("/api/status")
    def status() -> Json:
        return {"locked": store.locked, "demo": demo, "csrf": csrf, "version": "0.02"}

    @app.post("/api/session")
    def login(body: Json) -> JSONResponse:
        fields(body, {"token"})
        if not secrets.compare_digest(text(body, "token", 128), bootstrap):
            raise DomainError("서버가 열어준 브라우저 창에서 연결해주세요.", 401)
        response = JSONResponse({"authenticated": True})
        response.set_cookie(
            "whoiam_session", session, httponly=True, samesite="strict", path="/"
        )
        return response

    @app.get("/api/snapshot")
    def snapshot() -> Json:
        with store.mutex:
            last_activity = store.touched
            result = core.snapshot()
            store.touched = last_activity
            return result

    @app.post("/api/unlock")
    def unlock() -> Json:
        store.unlock()
        return {"locked": False}

    @app.post("/api/lock")
    def lock() -> Json:
        store.lock()
        return {"locked": True}

    @app.post("/api/commands")
    def command(body: Json) -> Json:
        fields(body, {"name", "data", "request_id"})
        if not isinstance(body.get("data"), dict):
            raise DomainError("명령 데이터를 확인해주세요.")
        return {
            "result": core.execute(
                text(body, "name", 64), body["data"], text(body, "request_id", 36)
            )
        }

    @app.get("/api/documents/{reference}")
    def document(reference: str) -> Response:
        document = core.sensitive.document(reference)
        suffix = {"application/pdf": "pdf", "image/png": "png", "image/jpeg": "jpg"}[
            document["media_type"]
        ]
        return Response(
            base64.b64decode(document["content"]),
            media_type=document["media_type"],
            headers={
                "Content-Disposition": f'attachment; filename="whoiam-document.{suffix}"'
            },
        )

    @app.get("/{asset:path}")
    def asset(asset: str) -> Response:
        selected = ASSETS.get(asset)
        if selected is None:
            return Response("Not found", status_code=404)
        path, media_type = selected
        response = Response((WEB_ROOT / path).read_bytes(), media_type=media_type)
        if path == "index.html" and demo:
            response.set_cookie(
                "whoiam_session", session, httponly=True, samesite="strict", path="/"
            )
        return response

    return app
