from fastapi import APIRouter, HTTPException, status
from typing import List, Annotated, Union
from app.main import settings
from app.session_manager import session_manager
from app.models import (
    PhoneNumber,
    SessionInfo,
    BaseModel,
    CodeVerification
)
import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

class AuthResponse(BaseModel):
    status: str
    message: str
    phone_code_hash: str | None = None

class SessionsResponse(BaseModel):
    sessions: List[SessionInfo]

class PasswordVerification(PhoneNumber):
    """2FA password verification request"""
    password: str

@router.post("/start", status_code=status.HTTP_200_OK, response_model=AuthResponse)
async def start_auth(request: PhoneNumber):
    """Start Telegram authentication process"""
    try:
        if not settings.API_ID or not settings.API_HASH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="API_ID and API_HASH are required. Please check your .env file."
            )

        status_code, phone_code_hash = await session_manager.start_auth(
            request.phone_number,
            settings.API_ID,
            settings.API_HASH
        )

        if status_code == "already_authorized":
            logger.info("Client already authorized")
            return AuthResponse(
                status="already_authorized",
                message="Account already authorized",
                phone_code_hash=None
            )
        else:
            logger.info(f"Auth code sent to {request.phone_number}")
            return AuthResponse(
                status="code_sent",
                message="Authentication code has been sent",
                phone_code_hash=phone_code_hash
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error during authentication start")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/verify-code", status_code=status.HTTP_200_OK, response_model=AuthResponse)
async def verify_code(verification: CodeVerification):
    """Verify the authentication code"""
    try:
        # Code validation is now handled by the model's validator
        logger.info(f"Attempting to verify code for {verification.phone_number}")
        logger.debug(f"Code verification details - Code: {verification.code}, Phone Code Hash: {verification.phone_code_hash}")

        status_code = await session_manager.verify_code(
            verification.phone_number,
            verification.code,
            verification.phone_code_hash
        )

        if status_code == "success":
            logger.info("Successfully signed in")
            return AuthResponse(
                status="success",
                message="Successfully authenticated"
            )
        elif status_code == "2fa_required":
            logger.info("Two-factor authentication required")
            return AuthResponse(
                status="2fa_required",
                message="Two-factor authentication is required"
            )
        else:
            logger.error(f"Unexpected status code during verification: {status_code}")
            raise ValueError(f"Unexpected authentication status: {status_code}")

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.exception("Unexpected error during code verification")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected authentication error: {str(e)}"
        )

@router.post("/verify-password", status_code=status.HTTP_200_OK, response_model=AuthResponse)
async def verify_password(verification: PasswordVerification):
    """Complete 2FA authentication"""
    try:
        await session_manager.verify_password(
            verification.phone_number,
            verification.password
        )
        return AuthResponse(
            status="success",
            message="Successfully authenticated"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error during password verification")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/list", response_model=SessionsResponse)
async def get_sessions():
    """List all registered Telegram accounts"""
    try:
        sessions = await session_manager.list_sessions()
        return SessionsResponse(sessions=sessions)
    except Exception as e:
        logger.exception("Error listing sessions")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/{phone_number}")
async def delete_session(phone_number: str):
    """Remove a Telegram account"""
    try:
        # Validate phone number format
        validated_phone = PhoneNumber(phone_number=phone_number).phone_number
        result = await session_manager.remove_session(validated_phone)
        return AuthResponse(
            status="success",
            message=result["message"]
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.exception("Error removing session")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
