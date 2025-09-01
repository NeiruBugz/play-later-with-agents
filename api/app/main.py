from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import WelcomeResponse
from app.exception_handlers import register_exception_handlers, request_id_middleware
from app.routers import health


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="A gaming backlog management application",
        version="0.1.0",
        debug=settings.debug,
    )

    # Request ID middleware for tracing
    app.middleware("http")(request_id_middleware)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers (standard error format)
    register_exception_handlers(app)

    # Include versioned routers
    app.include_router(health.router, prefix="/api/v1")

    # Root endpoint
    @app.get("/", response_model=WelcomeResponse)
    def read_root():
        return WelcomeResponse(message=f"Welcome to {settings.app_name}")

    return app


app = create_app()
