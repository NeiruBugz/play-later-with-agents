import logging.config
from pathlib import Path
from datetime import datetime, date
from typing import Any

import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import settings
from app.models import WelcomeResponse
from app.exception_handlers import register_exception_handlers, request_id_middleware
from app.routers import health, collection, playthroughs
from app.utils import format_datetime

# Load logging configuration
log_config_path = Path(__file__).parent.parent / "logging.yaml"
with open(log_config_path) as f:
    config = yaml.safe_load(f)
    logging.config.dictConfig(config)


# Custom JSON encoder for consistent timestamp formatting
class CustomJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        # Use our custom datetime formatter
        if isinstance(content, BaseModel):
            content = content.model_dump(mode="json")

        # Recursively format datetime objects in the content
        def format_datetimes(obj: Any) -> Any:
            if isinstance(obj, (datetime, date)):
                return format_datetime(obj)
            elif isinstance(obj, dict):
                return {k: format_datetimes(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [format_datetimes(item) for item in obj]
            return obj

        formatted_content = format_datetimes(content)
        return super().render(formatted_content)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="A gaming backlog management application",
        version="0.1.0",
        debug=settings.debug,
        default_response_class=CustomJSONResponse,
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
    app.include_router(collection.router, prefix="/api/v1")
    app.include_router(playthroughs.router, prefix="/api/v1")

    # Root endpoint
    @app.get("/", response_model=WelcomeResponse)
    def read_root():
        return WelcomeResponse(message=f"Welcome to {settings.app_name}")

    return app


app = create_app()
