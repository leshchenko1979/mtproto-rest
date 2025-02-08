import contextlib
import os
import json
import re
import logging
import sys
import ssl
import base64
from typing import Dict, Optional, Tuple, Any, List

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import User
from telethon.network import ConnectionTcpFull
from telethon.errors import (
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    SessionPasswordNeededError,
    FloodWaitError,
    RPCError,
    AuthKeyUnregisteredError,
    UserDeactivatedError
)
from fastapi import HTTPException, status

from .models import SessionInfo
from .main import settings
from .constants import APP_VERSION

# Get loggers without reconfiguring
logger = logging.getLogger(__name__)
telethon_logger = logging.getLogger("telethon")

# Add file handler for session manager logs
os.makedirs('logs', exist_ok=True)
file_handler = logging.FileHandler('logs/session_manager.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

logger.info("Session manager initialized")

def clean_session_string(session_string: str) -> str:
    """Clean and validate session string."""
    # Remove newlines and whitespace
    cleaned = ''.join(session_string.split())

    # Validate that it's a valid base64 string
    try:
        # The session string should be base64 encoded
        base64.b64decode(cleaned, validate=True)
        logger.debug(f"Session string validated, length: {len(cleaned)}")
        return cleaned
    except Exception as e:
        logger.error(f"Invalid session string format: {e}")
        raise ValueError("Invalid session string format") from e

class SessionManager:
    def __init__(self, sessions_dir: str = "sessions"):
        """Initialize session manager"""
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._clients: Dict[str, TelegramClient] = {}
        self._sessions_dir = sessions_dir
        self._load_sessions()

    def _load_sessions(self):
        """Load saved sessions from file"""
        try:
            os.makedirs(self._sessions_dir, exist_ok=True)
            session_file = os.path.join(self._sessions_dir, "sessions.json")
            if os.path.exists(session_file):
                with open(session_file, "r") as f:
                    self._sessions = json.load(f)
                logger.info(f"Loaded {len(self._sessions)} sessions from {session_file}")
            else:
                logger.info("No existing sessions file found")
        except Exception as e:
            logger.error(f"Error loading sessions: {e}")
            self._sessions = {}

    def _save_sessions(self):
        """Save sessions to file"""
        try:
            session_file = os.path.join(self._sessions_dir, "sessions.json")
            with open(session_file, "w") as f:
                json.dump(self._sessions, f)
            logger.info(f"Saved {len(self._sessions)} sessions to {session_file}")
        except Exception as e:
            logger.error(f"Error saving sessions: {e}")

    async def _create_client(self, phone_number: str, api_id: int, api_hash: str, session_string: Optional[str] = None) -> TelegramClient:
        """Create a new Telethon client"""
        try:
            logger.debug(f"Creating new client for {phone_number}")
            logger.debug(f"Parameters: api_id={api_id}, phone_number={phone_number}")

            if session_string:
                try:
                    # Clean and validate session string
                    cleaned_session = clean_session_string(session_string)
                    logger.debug("Session string cleaned and validated")
                    session = StringSession(cleaned_session)
                except Exception as e:
                    logger.error(f"Failed to process session string: {e}", exc_info=True)
                    raise ValueError(f"Invalid session string: {str(e)}") from e
            else:
                logger.debug("No session string provided, using memory session")
                session = StringSession()

            try:
                client = TelegramClient(
                    session=session,
                    api_id=api_id,
                    api_hash=api_hash,
                    connection=ConnectionTcpFull,
                    use_ipv6=False,
                    system_version="Windows 10",
                    app_version=APP_VERSION,
                    device_model="Desktop",
                    timeout=30
                )
            except Exception as e:
                logger.error(f"Failed to create TelegramClient: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to create TelegramClient: {str(e)}"
                ) from e

            try:
                # Connect to Telegram
                logger.debug("Connecting client...")
                await client.connect()

                # Check authorization
                if await client.is_user_authorized():
                    logger.debug("Client is authorized")
                else:
                    logger.debug("Client is not authorized")
            except Exception as e:
                logger.error(f"Failed to connect or check authorization: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to connect: {str(e)}"
                ) from e

            logger.info(f"Client successfully created and connected for {phone_number}")
            return client

        except Exception as e:
            logger.error(f"Error creating client for {phone_number}: {e}", exc_info=True)
            if hasattr(e, '__cause__') and e.__cause__:
                logger.error(f"Caused by: {e.__cause__}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create Telegram client for {phone_number}: {str(e)}"
            ) from e

    async def _cleanup_client(self, phone_number: str):
        """Clean up client resources"""
        if phone_number in self._clients:
            client = self._clients[phone_number]
            try:
                await client.disconnect()
                del self._clients[phone_number]
                logger.debug(f"Client for {phone_number} cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up client for {phone_number}: {e}")

    async def get_client(self, phone_number: str, api_id: int, api_hash: str) -> TelegramClient:
        """Get a client for operations, creating a new one if needed"""
        session = self._sessions.get(phone_number)
        if not session or not session.get("session_string"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found for {phone_number}. Please authenticate first."
            )

        await self._cleanup_client(phone_number)

        try:
            client = await self._create_client(phone_number, api_id, api_hash, session["session_string"])
            self._clients[phone_number] = client
            return client
        except Exception as e:
            logger.error(f"Error creating client: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create client: {str(e)}"
            ) from e

    async def start_auth(self, phone_number: str, api_id: int, api_hash: str) -> Tuple[str, Optional[str]]:
        """Start authentication process"""
        try:
            # Check if already authorized
            if phone_number in self._sessions and self._sessions[phone_number].get("session_string"):
                logger.info(f"Authentication skipped: Client {phone_number} already authorized")
                return "already_authorized", None

            logger.debug(f"Cleaning up any existing client for {phone_number}")
            await self._cleanup_client(phone_number)

            logger.info(f"Initiating authentication for {phone_number}")
            logger.debug(f"Creating client with API ID: {api_id}")
            client = await self._create_client(phone_number, api_id, api_hash)

            try:
                # Check if already authorized
                logger.debug("Checking if client is already authorized")
                if await client.is_user_authorized():
                    logger.info(f"Client {phone_number} was already authorized")
                    logger.debug("Getting user info")
                    me = await client.get_me()
                    logger.debug("Getting session string")
                    session_string = client.session.save()
                    self._sessions[phone_number] = {
                        "session_string": session_string,
                        "user_id": me.id,
                        "username": getattr(me, 'username', None)
                    }
                    logger.debug("Saving sessions")
                    self._save_sessions()
                    return "already_authorized", None

                # Not authorized, send code
                logger.debug(f"Starting send code process for {phone_number}")
                sent_code = await client.send_code_request(phone_number)
                logger.info(f"Authentication code sent successfully to {phone_number}")
                logger.debug(f"Phone code hash received: {sent_code.phone_code_hash[:8]}...")

                # Store client for later use
                logger.debug("Storing client and initializing session")
                self._clients[phone_number] = client
                self._sessions[phone_number] = {
                    "session_string": None,
                    "user_id": None,
                    "username": None
                }
                logger.debug("Saving sessions")
                self._save_sessions()
                return "code_sent", sent_code.phone_code_hash

            except Exception as e:
                logger.error(f"Error in authentication process: {e}", exc_info=True)
                await self._cleanup_client(phone_number)
                raise

        except Exception as e:
            logger.error(f"Error starting authentication: {e}", exc_info=True)
            if hasattr(e, '__cause__') and e.__cause__:
                logger.error(f"Caused by: {e.__cause__}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to start authentication: {str(e)}"
            ) from e

    async def complete_auth(self, phone_number: str, code: str, phone_code_hash: str) -> SessionInfo:
        """Complete the authentication process with the received code"""
        if phone_number not in self._clients:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No pending authentication found for this phone number"
            )

        client = self._clients[phone_number]
        try:
            # Sign in with code
            try:
                user = await client.sign_in(phone_number, code, phone_code_hash=phone_code_hash)
            except SessionPasswordNeededError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="2FA password required"
                ) from e
            except (PhoneCodeInvalidError, PhoneCodeExpiredError) as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )

            # Get session string using Telethon's StringSession
            session = StringSession.save(client.session)
            logger.debug(f"Created new Telethon session string, length: {len(session)}")

            self._sessions[phone_number] = {
                "session_string": session,
                "user_id": user.id,
                "username": user.username
            }
            self._save_sessions()

            return SessionInfo(
                phone_number=phone_number,
                session_string=session,
                user_id=user.id,
                username=user.username
            )

        except Exception as e:
            logger.error(f"Error completing authentication: {e}")
            if not isinstance(e, HTTPException):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to complete authentication: {str(e)}"
                ) from e
            raise
        finally:
            await self._cleanup_client(phone_number)

    async def complete_2fa(self, phone_number: str, password: str) -> SessionInfo:
        """Complete two-factor authentication with password"""
        if phone_number not in self._clients:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No pending authentication found for this phone number"
            )

        client = self._clients[phone_number]
        try:
            # Sign in with 2FA password
            user = await client.sign_in(password=password)

            # Get session string and user info
            session_string = client.session.save()
            self._sessions[phone_number] = {
                "session_string": session_string,
                "user_id": user.id,
                "username": user.username
            }
            self._save_sessions()

            return SessionInfo(
                phone_number=phone_number,
                session_string=session_string,
                user_id=user.id,
                username=user.username
            )

        except Exception as e:
            logger.error(f"Error completing 2FA: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to complete 2FA: {str(e)}"
            ) from e
        finally:
            await self._cleanup_client(phone_number)

    async def list_sessions(self) -> List[SessionInfo]:
        """List all active sessions"""
        return [
            SessionInfo(
                phone_number=phone,
                session_string=info["session_string"],
                user_id=info["user_id"],
                username=info.get("username")
            )
            for phone, info in self._sessions.items()
            if info.get("session_string")
        ]

    async def remove_session(self, phone_number: str) -> dict:
        """Remove a session and clean up all associated clients"""
        if phone_number not in self._sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )

        await self._cleanup_client(phone_number)
        del self._sessions[phone_number]
        self._save_sessions()

        return {"message": "Session removed successfully"}


# Create a singleton instance of SessionManager
session_manager = SessionManager()
