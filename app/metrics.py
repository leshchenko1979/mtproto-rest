import logging
import logfire
from typing import Any

logger = logging.getLogger(__name__)

def track_auth_attempt(phone_number: str, success: bool, details: str | None = None) -> None:
    """Track authentication attempts"""
    try:
        logger.info(f"Auth attempt: {phone_number} - {'Success' if success else 'Failed'} - {details or 'No details'}")
        logfire.log(
            "auth_attempt",
            {
                "phone_number": phone_number,
                "success": success,
                "details": details
            }
        )
    except Exception as e:
        logger.error(f"Failed to track auth attempt: {e}")

def track_session_operation(operation: str, phone_number: str, success: bool, details: Any = None) -> None:
    """Track session operations like create, delete, etc."""
    try:
        logger.info(f"Session operation: {operation} - {phone_number} - {'Success' if success else 'Failed'} - {details or 'No details'}")
        logfire.log(
            "session_operation",
            {
                "operation": operation,
                "phone_number": phone_number,
                "success": success,
                "details": str(details) if details else None
            }
        )
    except Exception as e:
        logger.error(f"Failed to track session operation: {e}")
