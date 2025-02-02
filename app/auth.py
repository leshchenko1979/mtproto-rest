from typing import Dict, Optional, Any
from fastapi import HTTPException, status
from pyrogram import Client
from pathlib import Path
import os
import json
import asyncio
from .models import PhoneNumber, SessionInfo

class AuthRequest(PhoneNumber):
    """Authentication request with phone number"""
    pass

class CodeVerification(PhoneNumber):
    """Code verification request"""
    code: str
    phone_code_hash: str

class PasswordVerification(PhoneNumber):
    """2FA password verification request"""
    password: str

# File paths configuration
BASE_DIR = Path(__file__).parent.parent
SESSIONS_DIR = BASE_DIR / "sessions"
SESSIONS_INFO_FILE = SESSIONS_DIR / "sessions.json"

# Active clients during authentication
active_auth_clients: Dict[str, Client] = {}

def _ensure_sessions_dir() -> None:
    """Ensure sessions directory exists"""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

def load_sessions_info() -> dict:
    """Load sessions metadata from file"""
    _ensure_sessions_dir()
    if SESSIONS_INFO_FILE.exists():
        try:
            return json.loads(SESSIONS_INFO_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}

def save_sessions_info(sessions: dict) -> None:
    """Save sessions metadata to file"""
    _ensure_sessions_dir()
    SESSIONS_INFO_FILE.write_text(json.dumps(sessions, indent=2))

async def _create_client(
    session_string: Optional[str] = None,
    in_memory: bool = True,
    takeout: bool = False
) -> Client:
    """Create a Pyrogram client with given configuration"""
    try:
        return Client(
            name=":memory:" if in_memory else "telegram_session",
            session_string=session_string,
            api_id=os.getenv("API_ID"),
            api_hash=os.getenv("API_HASH"),
            in_memory=in_memory,
            takeout=takeout,
            no_updates=True
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create client: {str(e)}"
        )

async def start_auth(phone_number: str) -> dict:
    """Start authentication process for a new account"""
    try:
        client = await _create_client()
        await client.connect()

        sent_code = await client.send_code(phone_number)
        active_auth_clients[phone_number] = client

        return {
            "message": "Code sent to phone number",
            "phone_code_hash": sent_code.phone_code_hash
        }

    except Exception as e:
        if phone_number in active_auth_clients:
            await active_auth_clients[phone_number].disconnect()
            del active_auth_clients[phone_number]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

async def verify_code(verification: CodeVerification) -> dict:
    """Verify the code and potentially trigger 2FA"""
    client = active_auth_clients.get(verification.phone_number)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication session expired. Please start over."
        )

    try:
        await client.sign_in(
            verification.phone_number,
            verification.phone_code_hash,
            verification.code
        )

        # If we get here without exception, no 2FA is required
        me = await client.get_me()
        session_string = await client.export_session_string()
        await client.disconnect()
        del active_auth_clients[verification.phone_number]

        # Save session info
        sessions = load_sessions_info()
        sessions[verification.phone_number] = {
            "session_string": session_string,
            "user_id": me.id,
            "username": me.username
        }
        save_sessions_info(sessions)

        return {
            "message": "Authentication successful",
            "session_string": session_string,
            "user": {
                "id": me.id,
                "username": me.username,
                "phone_number": verification.phone_number
            }
        }

    except Exception as e:
        error_message = str(e).lower()
        if "password" in error_message or "2fa" in error_message:
            return {
                "message": "2FA password required",
                "requires_password": True
            }

        await client.disconnect()
        del active_auth_clients[verification.phone_number]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

async def verify_password(verification: PasswordVerification) -> dict:
    """Complete 2FA authentication"""
    client = active_auth_clients.get(verification.phone_number)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication session expired. Please start over."
        )

    try:
        await client.check_password(verification.password)
        me = await client.get_me()
        session_string = await client.export_session_string()
        await client.disconnect()
        del active_auth_clients[verification.phone_number]

        # Save session info
        sessions = load_sessions_info()
        sessions[verification.phone_number] = {
            "session_string": session_string,
            "user_id": me.id,
            "username": me.username
        }
        save_sessions_info(sessions)

        return {
            "message": "Authentication successful",
            "session_string": session_string,
            "user": {
                "id": me.id,
                "username": me.username,
                "phone_number": verification.phone_number
            }
        }

    except Exception as e:
        await client.disconnect()
        del active_auth_clients[verification.phone_number]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

async def get_client(session_string: str) -> Client:
    """Create a Pyrogram client from session string"""
    return await _create_client(session_string=session_string)

async def list_sessions() -> list[SessionInfo]:
    """List all active sessions"""
    sessions = load_sessions_info()
    return [
        SessionInfo(
            phone_number=phone,
            session_string=info["session_string"],
            user_id=info["user_id"],
            username=info.get("username")
        )
        for phone, info in sessions.items()
    ]

async def remove_session(phone_number: str) -> dict:
    """Remove a session by phone number"""
    sessions = load_sessions_info()
    if phone_number not in sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    del sessions[phone_number]
    save_sessions_info(sessions)
    return {"message": "Session removed successfully"}
