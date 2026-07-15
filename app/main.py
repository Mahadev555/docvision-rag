"""FastAPI application factory and ASGI entry point.

Run locally with:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app import __version__
from app.config import settings
from app.exceptions import AppError
from app.logger import get_logger, setup_logging
from app.routes import chat, documents, health

logger = get_logger("app")


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application."""
    setup_logging()

    app = FastAPI(
        title=f"{settings.app_name} API",
        version=__version__,
        description=(
            "DocVision — Multimodal Document Intelligence Platform. "
            "Makes diagrams, screenshots and figures inside PDFs semantically searchable."
        ),
        default_response_class=ORJSONResponse,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> ORJSONResponse:
        logger.warning("app error: %s", exc.message)
        return ORJSONResponse(status_code=exc.status_code, content={"error": exc.message})

    app.include_router(health.router, prefix=settings.api_v1_prefix)
    app.include_router(documents.router, prefix=settings.api_v1_prefix)
    app.include_router(chat.router, prefix=settings.api_v1_prefix)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "version": __version__,
            "docs": "/docs",
            "health": f"{settings.api_v1_prefix}/health",
        }

    return app


app = create_app()
