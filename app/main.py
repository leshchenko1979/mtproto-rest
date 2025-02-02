from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    # Telegram credentials
    API_ID: int
    API_HASH: str

    # Logfire settings
    LOGFIRE_TOKEN: str | None = None

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    class Config:
        env_file = ".env"

settings = Settings()

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="Telegram REST API",
        description="REST API for Telegram MTProto functionality",
        version="1.0.0"
    )

    # Configure Logfire if API key is present
    if settings.LOGFIRE_TOKEN:
        import logfire
        logfire.configure(environment="production")
        logfire.instrument_fastapi(app)

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    from app.routes import auth, search
    app.include_router(auth.router)
    app.include_router(search.router)

    return app

app = create_app()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "version": app.version,
        "logfire_enabled": bool(settings.LOGFIRE_TOKEN)
    }
