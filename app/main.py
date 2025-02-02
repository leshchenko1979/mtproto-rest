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
    ENVIRONMENT: str = "production"

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS_COUNT: int = 1
    RELOAD: bool = False

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
        },
    },
    "loggers": {
        "app": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "": {
            "handlers": ["console"],
            "level": "WARNING",
        },
    },
}

logger = logging.getLogger("app")

def setup_logging() -> None:
    """Configure logging"""
    try:
        logging.config.dictConfig(LOGGING_CONFIG)
    except Exception as e:
        logging.basicConfig(level="INFO")
        logger.exception("Failed to configure logging")

def setup_logfire() -> bool:
    """Configure Logfire integration"""
    if not settings.LOGFIRE_TOKEN:
        logger.warning("LOGFIRE_TOKEN not set")
        return False

    try:
        logfire.configure(
            token=settings.LOGFIRE_TOKEN,
            environment=settings.ENVIRONMENT
        )
        logfire.info("Logfire configuration test", service=APP_NAME)
        logger.info("Logfire configured successfully")
        return True
    except Exception as e:
        logger.exception("Logfire configuration failed")
        return False

def configure_middleware(app: FastAPI) -> None:
    """Configure middleware"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

def configure_routes(app: FastAPI) -> None:
    """Configure routes"""
    from app.routes import auth, search
    app.include_router(auth.router)
    app.include_router(search.router)

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    setup_logging()

    app = FastAPI(
        title=APP_NAME,
        description=APP_DESCRIPTION,
        version=APP_VERSION
    )

    if setup_logfire():
        try:
            logfire.instrument_fastapi(app)
            logger.info("FastAPI instrumented with Logfire")
        except Exception as e:
            logger.exception("FastAPI Logfire instrumentation failed")

    configure_middleware(app)
    configure_routes(app)

    return app

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

    if settings.LOGFIRE_TOKEN:
        try:
            logfire.info("Health check performed", **status_info)
        except Exception as e:
            logger.exception("Failed to log to Logfire")

    return status_info
