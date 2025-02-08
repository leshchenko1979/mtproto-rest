from fastapi import FastAPI, status, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import logfire
import os
from typing import Dict, Any
from pydantic_settings import BaseSettings
from .constants import APP_NAME, APP_VERSION, APP_DESCRIPTION

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


# Create settings instance
settings = Settings()

# Configure base logging - minimal for production to reduce noise
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "DEBUG"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/debug.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Set up logfire for production logging
if settings.LOGFIRE_TOKEN:
    try:
        # Configure Logfire with production settings
        logfire.configure(
            token=settings.LOGFIRE_TOKEN,
            environment=settings.ENVIRONMENT or "production",
            service_name=APP_NAME,
            service_version=APP_VERSION
        )
        logger.info("Logfire configured successfully", extra={
            "logfire_enabled": True,
            "environment": settings.ENVIRONMENT,
            "log_level": os.getenv("LOG_LEVEL", "INFO")
        })
    except Exception as e:
        logger.error(f"Failed to configure Logfire: {e}", exc_info=True)
else:
    logger.warning("Logfire token not provided, running without Logfire integration")

# Log application startup
logger.info(f"Starting {APP_NAME} in {settings.ENVIRONMENT or 'production'} mode")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title=APP_NAME,
        description=APP_DESCRIPTION,
        version=APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # Add exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "docs_url": "https://github.com/leshchenko1979/mtproto-rest"
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": str(exc),
                "docs_url": "https://github.com/leshchenko1979/mtproto-rest"
            }
        )

    @app.exception_handler(Exception)
    async def catch_all_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error. Please check the documentation for proper API usage.",
                "docs_url": "https://github.com/leshchenko1979/mtproto-rest"
            }
        )

    # Set up CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Import and include routers
    from app.routes import auth, forward, search
    app.include_router(auth.router)
    app.include_router(forward.router)
    app.include_router(search.router)

    # Instrument FastAPI with Logfire
    if settings.LOGFIRE_TOKEN:
        logfire.instrument_fastapi(app)

    return app


app = create_app()


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    return {
        "status": "ok",
        "version": APP_VERSION,
        "logfire_enabled": bool(settings.LOGFIRE_TOKEN),
        "environment": settings.ENVIRONMENT,
    }
