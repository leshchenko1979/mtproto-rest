# Development server runner
import os

# Force development environment for local runs
os.environ["ENVIRONMENT"] = "development"

import uvicorn
import logging
import logging.config
from app.main import settings, APP_NAME


class DetailedFormatter(logging.Formatter):
    def format(self, record):
        # Format the message with timestamp, level, etc.
        formatted = super().format(record)

        # Only append exception info if it exists
        if record.exc_info:
            # Get exception formatted text
            exc_text = self.formatException(record.exc_info)
            # Append it to the message
            formatted = f"{formatted}\n{exc_text}"

        return formatted


# Development logging configuration - more verbose for debugging
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "detailed": {
            "()": DetailedFormatter,
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "detailed",
            "stream": "ext://sys.stdout",
            "level": "DEBUG",
        },
        "file": {
            "class": "logging.FileHandler",
            "formatter": "detailed",
            "filename": "logs/development.log",
            "mode": "a",
            "level": "DEBUG",
        }
    },
    "loggers": {
        "app": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False  # Prevent propagation to root logger
        },
        "uvicorn": {
            "handlers": ["console"],  # Only console for uvicorn
            "level": "INFO",
            "propagate": False
        },
        "telethon": {
            "handlers": ["console", "file"],
            "level": "INFO",  # Reduce telethon logging noise
            "propagate": False
        },
        "": {  # Root logger - catch all other loggers
            "handlers": ["console", "file"],
            "level": "INFO"  # Less verbose for unknown loggers
        },
    },
}

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Apply development logging configuration
logging.config.dictConfig(LOGGING_CONFIG)

# Get the logger for this module
logger = logging.getLogger("app")
logger.info(f"Starting {APP_NAME} in development mode")

if __name__ == "__main__":
    try:
        uvicorn.run(
            "app.main:app",
            host=settings.HOST,
            port=settings.PORT,
            workers=1,  # Force single worker for development
            timeout_keep_alive=75,
            timeout_graceful_shutdown=30,
            limit_concurrency=1000,
            backlog=2048,
            reload=True,  # Enable auto-reload for development
            log_level="warning",  # Reduce Uvicorn logging noise
            access_log=False,  # Disable access logs since we use Logfire
            proxy_headers=True,
            forwarded_allow_ips="*",
            server_header=False,
        )
    except Exception as e:
        logger.exception("Application failed to start")
        raise  # Re-raise the exception to ensure the process exits with error
