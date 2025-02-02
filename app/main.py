from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="Telegram REST API",
        description="REST API for Telegram MTProto functionality",
        version="1.0.0"
    )

    # Configure Logfire if API key is present
    if os.getenv("LOGFIRE_TOKEN"):
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
        "logfire_enabled": bool(os.getenv("LOGFIRE_TOKEN"))
    }
