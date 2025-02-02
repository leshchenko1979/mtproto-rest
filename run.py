import uvicorn
import logging
from app.main import app
import os

# Configure logging
logging.basicConfig(level=logging.WARNING)  # Set high level for all loggers by default

# Get the app logger and prevent propagation to root logger
app_logger = logging.getLogger("app")
app_logger.setLevel(logging.DEBUG)
app_logger.propagate = False  # Prevent propagation to root logger

# Create console handler with formatter
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_handler.setFormatter(formatter)

# Add handler to app logger
app_logger.addHandler(console_handler)

# Configure Logfire if API key is present
logfire_api_key = os.getenv("LOGFIRE_API_KEY")
if logfire_api_key:
    try:
        import logfire
        logfire.configure(logfire_api_key)
        logfire.instrument_fastapi(app)
    except Exception as e:
        app_logger.error(f"Failed to configure Logfire: {e}")

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="warning"  # Set Uvicorn log level to warning
    )
