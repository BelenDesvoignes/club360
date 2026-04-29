import os
import sys
from typing import Optional


# Vercel runs this file as the Serverless Function entrypoint.
# Ensure imports work regardless of working directory.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")

# Make `backend/` importable so that `app.*` resolves to `backend/app/*`.
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.requests import Request


_BOOT_ERROR: Optional[Exception] = None
backend_app = None

try:
    from app.main import app as backend_app  # type: ignore
except Exception as exc:  # pragma: no cover
    _BOOT_ERROR = exc


# Expose an ASGI app for Vercel.
# In production we want endpoints under `/api/*`.
app = FastAPI()

if backend_app is not None:
    app.mount("/api", backend_app)
else:
    # If the backend fails to import (missing deps, syntax error, etc.),
    # Vercel otherwise returns a blank 500 text/plain.
    @app.api_route(
        "/api/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )
    async def _boot_failed(_request: Request, path: str):
        message = str(_BOOT_ERROR) if _BOOT_ERROR is not None else "Unknown"
        return JSONResponse(
            status_code=500,
            content={
                "error": "BOOT_FAILED",
                "type": _BOOT_ERROR.__class__.__name__ if _BOOT_ERROR else "Unknown",
                "message": message[:500],
                "path": "/api/" + path,
            },
        )
