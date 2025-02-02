import os
import json
import logging
from datetime import datetime, UTC
from typing import Any, Dict, Optional
import httpx
from fastapi import Request, Response
from pydantic import BaseModel

class LogfireHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("LOGFIRE_API_KEY")
        self.url = "https://in.logfire.sh/api/logs"
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )

    async def async_emit(self, record: logging.LogRecord):
        try:
            log_entry = {
                "level": record.levelname,
                "message": self.format(record),
                "timestamp": datetime.utcfromtimestamp(record.created).isoformat(),
                "logger": record.name,
                "extra": getattr(record, "extra", {}),
            }

            await self.client.post(self.url, json=log_entry)
        except Exception as e:
            print(f"Failed to send log to Logfire: {e}")

    def emit(self, record):
        # This is called in sync context, but we need async
        # We'll just print to stdout in this case
        print(f"[{record.levelname}] {self.format(record)}")

class RequestLogMiddleware:
    async def __call__(
        self,
        request: Request,
        call_next: Any
    ) -> Response:
        start_time = datetime.now(UTC)

        # Get request body if it exists
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.json()
            except:
                pass

        response = await call_next(request)

        duration = (datetime.now(UTC) - start_time).total_seconds()

        # Log the request
        log_data = {
            "request": {
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "body": body
            },
            "response": {
                "status_code": response.status_code,
                "duration": duration
            },
            "client": {
                "host": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent")
            }
        }

        await log_request(log_data)

        return response

async def setup_logging():
    """Initialize logging configuration"""
    handler = LogfireHandler()
    handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    return handler

async def log_request(data: Dict[str, Any]):
    """Log API request details"""
    logger = logging.getLogger("api.request")
    logger.info("API Request", extra={"data": data})

async def log_auth_event(
    event_type: str,
    phone_number: str,
    success: bool,
    error: Optional[str] = None
):
    """Log authentication events"""
    logger = logging.getLogger("auth")
    logger.info(
        f"Authentication event: {event_type}",
        extra={
            "event_type": event_type,
            "phone_number": phone_number,
            "success": success,
            "error": error
        }
    )

async def log_search_event(
    session_id: str,
    search_type: str,
    query: str,
    results_count: int,
    duration: float,
    filters: Optional[Dict] = None
):
    """Log search operations"""
    logger = logging.getLogger("search")
    logger.info(
        f"Search operation: {search_type}",
        extra={
            "session_id": session_id,
            "search_type": search_type,
            "query": query,
            "results_count": results_count,
            "duration": duration,
            "filters": filters
        }
    )

async def log_error(
    error_type: str,
    error_message: str,
    context: Optional[Dict] = None
):
    """Log error events"""
    logger = logging.getLogger("error")
    logger.error(
        f"Error: {error_type}",
        extra={
            "error_type": error_type,
            "error_message": error_message,
            "context": context
        }
    )
