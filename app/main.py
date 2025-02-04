from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
import logging.config
import logfire
from typing import Dict, Any
from pydantic_settings import BaseSettings

# Constants
APP_NAME = "telegram-rest-api"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "REST API for Telegram MTProto functionality"

class Settings(BaseSettings):
    """Application settings"""
    # Telegram credentials
    API_ID: int
    API_HASH: str

    # Logfire settings
    LOGFIRE_TOKEN: str | None = None
    ENVIRONMENT: str | None = None

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = False  # Disable reload by default for production

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()

# Logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
            "level": "INFO"
        },
    },
    "loggers": {
        "app": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "pyrogram": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "uvicorn": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "": {  # Root logger
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        }
    }
}

def setup_logging():
    """Configure logging settings"""
    # Clear all existing handlers
    logging.getLogger().handlers.clear()

    # Apply configuration
    logging.config.dictConfig(LOGGING_CONFIG)

    if settings.LOGFIRE_TOKEN:
        logger.info("Logfire token set, configuring Logfire")
        logfire.configure(
            token=settings.LOGFIRE_TOKEN,
            environment=settings.ENVIRONMENT
        )
    else:
        logger.info("Logfire token not set, skipping configuration")


def configure_middleware(app: FastAPI):
    """Configure CORS and other middleware"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

def configure_routes(app: FastAPI):
    """Configure API routes"""
    from app.routes import auth, search, forward
    app.include_router(auth.router)
    app.include_router(search.router)
    app.include_router(forward.router)

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    setup_logging()

    app = FastAPI(
        title=APP_NAME,
        description=APP_DESCRIPTION,
        version=APP_VERSION
    )

    logfire.instrument_fastapi(app)

    configure_middleware(app)
    configure_routes(app)

    return app

# Get logger after logging configuration
logger = logging.getLogger(__name__)

app = create_app()

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    status_info = {
        "status": "ok",
        "version": APP_VERSION,
        "logfire_enabled": bool(settings.LOGFIRE_TOKEN),
        "environment": settings.ENVIRONMENT
    }

    logger.info("Health check performed", extra=status_info)

    return status_info
