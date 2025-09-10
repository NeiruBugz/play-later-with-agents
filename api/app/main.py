import logging.config
from pathlib import Path
from datetime import datetime, date

import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import WelcomeResponse
from app.exception_handlers import register_exception_handlers, request_id_middleware
from app.routers import health, collection, playthroughs
from app.utils import format_datetime

# Load logging configuration
log_config_path = Path(__file__).resolve().parent.parent / "logging.yaml"
try:
    with open(log_config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
        logging.config.dictConfig(config)
except FileNotFoundError:
    logging.basicConfig(level=logging.INFO)
except Exception as exc:  # pylint: disable=broad-exception-caught
    logging.basicConfig(level=logging.INFO)
    logging.getLogger(__name__).warning("Failed to load logging.yaml: %s", exc)


# Configure global JSON encoder for datetime objects
def setup_json_encoder():
    """Configure FastAPI to use consistent datetime serialization"""
    from fastapi.encoders import jsonable_encoder  # pylint: disable=import-outside-toplevel

    # Store original encoder
    original_jsonable_encoder = jsonable_encoder

    def custom_jsonable_encoder(obj, **kwargs):
        # Only handle datetime and date objects,
        # defer everything else to original encoder
        if isinstance(obj, (datetime, date)):
            return format_datetime(obj)
        return original_jsonable_encoder(obj, **kwargs)

    # Monkey patch the encoder
    import fastapi.encoders  # pylint: disable=import-outside-toplevel

    fastapi.encoders.jsonable_encoder = custom_jsonable_encoder


def create_app() -> FastAPI:
    # Setup custom JSON encoding for datetime objects
    setup_json_encoder()

    fastapi_app = FastAPI(
        title=settings.app_name,
        description="A gaming backlog management application",
        version="0.1.0",
        debug=settings.debug,
    )

    # Request ID middleware for tracing
    fastapi_app.middleware("http")(request_id_middleware)

    # Add CORS middleware
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers (standard error format)
    register_exception_handlers(fastapi_app)

    # Include versioned routers
    fastapi_app.include_router(health.router, prefix="/api/v1")
    fastapi_app.include_router(collection.router, prefix="/api/v1")
    fastapi_app.include_router(playthroughs.router, prefix="/api/v1")

    # Root endpoint
    @fastapi_app.get("/", response_model=WelcomeResponse)
    def read_root():
        return WelcomeResponse(message=f"Welcome to {settings.app_name}")

    return fastapi_app


app = create_app()
