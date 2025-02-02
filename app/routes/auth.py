from fastapi import APIRouter, HTTPException
from ..auth import (
    AuthRequest,
    CodeVerification,
    PasswordVerification,
    start_auth,
    verify_code,
    verify_password,
    list_sessions,
    remove_session
)

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

@router.post("/start")
async def start_authentication(auth_request: AuthRequest):
    """Start the authentication process for a new Telegram account"""
    return await start_auth(auth_request.phone_number)

@router.post("/verify-code")
async def verify_authentication_code(verification: CodeVerification):
    """Verify the authentication code and check if 2FA is required"""
    return await verify_code(verification)

@router.post("/verify-password")
async def verify_2fa_password(verification: PasswordVerification):
    """Complete authentication with 2FA password"""
    return await verify_password(verification)

@router.get("/list")
async def get_sessions():
    """List all registered Telegram accounts"""
    return await list_sessions()

@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Remove a Telegram account"""
    return await remove_session(session_id)
