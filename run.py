import uvicorn
import logging
from app.main import app, settings

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
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n%(exc_info)s',  # Add exc_info to show tracebacks
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_handler.setFormatter(formatter)

# Add handler to app logger
app_logger.addHandler(console_handler)

if __name__ == "__main__":
    try:
        uvicorn.run(
            "app.main:app",
            host=settings.HOST,
            port=settings.PORT,
            workers=settings.WORKERS_COUNT,
            timeout_keep_alive=75,
            timeout_graceful_shutdown=30,
            limit_concurrency=1000,
            backlog=2048,
            reload=True,
            log_level="warning",  # Reduce Uvicorn logging noise
            access_log=False,  # Disable access logs since we use Logfire
            proxy_headers=True,
            forwarded_allow_ips="*",
            server_header=False
        )
    except Exception as e:
        app_logger.exception("Application failed to start")  # This will automatically include traceback
        raise  # Re-raise the exception to ensure the process exits with error
