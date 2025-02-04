import contextlib
from pyrogram import Client
from pyrogram.errors import (
    PhoneCodeInvalid,
    PhoneCodeExpired,
    PhoneCodeEmpty,
    SessionPasswordNeeded,
    FloodWait
)
import os
import json
from typing import Dict, Optional, Tuple, List
import logging
from fastapi import HTTPException, status
from .models import SessionInfo
import re
import asyncio

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self, sessions_dir: str = "sessions"):
        self.sessions_dir = sessions_dir
        self.sessions_file = os.path.join(sessions_dir, "sessions.json")
        os.makedirs(sessions_dir, exist_ok=True)
        self._sessions: Dict[str, dict] = self._load_sessions()
        self._clients: Dict[str, Client] = {}

    def _load_sessions(self) -> Dict[str, dict]:
        """Load sessions from JSON file"""
        if os.path.exists(self.sessions_file):
            try:
                with open(self.sessions_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading sessions: {e}")
                return {}
        return {}

    def _save_sessions(self):
        """Save sessions to JSON file"""
        try:
            with open(self.sessions_file, 'w') as f:
                json.dump(self._sessions, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving sessions: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save session information",
            ) from e

    async def _create_client(self, phone_number: str, api_id: int, api_hash: str, session_string: Optional[str] = None) -> Client:
        """Create a new Pyrogram client"""
        try:
            # Use phone number in session name for better identification
            session_name = (
                f"session_{phone_number}"
                if not session_string
                else ":memory:"
            )

            return Client(
                name=session_name,
                session_string=session_string,
                api_id=api_id,
                api_hash=api_hash,
                no_updates=True,
                in_memory=bool(session_string),
            )
        except Exception as e:
            logger.error(f"Error creating client for {phone_number}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create Telegram client for {phone_number}: {str(e)}",
            ) from e

    async def _cleanup_client(self, phone_number: str):
        """Clean up client resources"""
        if phone_number in self._clients:
            client = self._clients[phone_number]
            try:
                if client.is_connected:
                    await client.disconnect()
                await client.storage.close()
                del self._clients[phone_number]
                logger.debug(f"Client for {phone_number} cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up client for {phone_number}: {e}")

    async def get_client(self, phone_number: str, api_id: int, api_hash: str) -> Client:
        """Get a client for operations, creating a new one if needed"""
        session = self._sessions.get(phone_number)
        if not session or not session.get("session_string"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found for {phone_number}. Please authenticate first."
            )

        # Clean up existing client if any
        await self._cleanup_client(phone_number)

        try:
            client = await self._create_client(phone_number, api_id, api_hash, session["session_string"])
            with contextlib.suppress(ConnectionError):
                await client.connect()

            self._clients[phone_number] = client
            return client
        except Exception as e:
            logger.error(f"Error creating client: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create client: {str(e)}",
            ) from e

    async def start_auth(self, phone_number: str, api_id: int, api_hash: str) -> Tuple[str, Optional[str]]:
        """Start authentication process"""
        try:
            # Check if already authorized
            if phone_number in self._sessions and self._sessions[phone_number].get("session_string"):
                logger.info(f"Authentication skipped: Client {phone_number} already authorized")
                return "already_authorized", None

            # Clean up any existing client
            await self._cleanup_client(phone_number)

            logger.info(f"Initiating authentication for {phone_number}")
            client = await self._create_client(phone_number, api_id, api_hash)

            try:
                logger.debug(f"Connecting client for {phone_number}")
                await client.connect()
            except ConnectionError:
                logger.debug(f"Client for {phone_number} already connected")
            if not client.is_connected:
                logger.error(f"Failed to connect client for {phone_number}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to connect Telegram client for {phone_number}"
                )

            try:
                logger.info(f"Sending authentication code to {phone_number}")
                sent = await client.send_code(phone_number)
                logger.info(f"Authentication code sent successfully to {phone_number}")

                self._clients[phone_number] = client
                self._sessions[phone_number] = {
                    "session_string": None,
                    "user_id": None,
                    "username": None
                }
                self._save_sessions()

                return "code_sent", sent.phone_code_hash
            except Exception as e:
                logger.error(f"Failed to send authentication code for {phone_number}: {str(e)}")
                await self._cleanup_client(phone_number)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to send authentication code: {str(e)}",
                ) from e

        except Exception as e:
            logger.error(f"Unexpected error during authentication start for {phone_number}: {str(e)}", exc_info=True)
            await self._cleanup_client(phone_number)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Authentication initialization failed: {str(e)}",
            ) from e

    async def verify_code(self, phone_number: str, code: str, phone_code_hash: str) -> str:
        """Verify authentication code with precise Pyrogram authentication and exception handling"""
        logger.info(f"Starting code verification for {phone_number}")
        logger.debug(f"Verification details - Code: {code}, Phone Code Hash: {phone_code_hash}")

        if phone_number not in self._clients:
            logger.error(f"No active client found for {phone_number}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active authentication session found. Please restart the authentication process."
            )

        client = self._clients[phone_number]
        try:
            # Ensure client is connected
            if not client.is_connected:
                logger.debug(f"Connecting client for {phone_number}")
                await client.connect()

            # Validate inputs
            if not code or not phone_code_hash:
                logger.error(f"Missing authentication code or hash for {phone_number}")
                raise ValueError("Authentication code and phone code hash are required")

            # Ensure code is a string and stripped
            code_str = code.strip()

            try:
                # Use Pyrogram's sign_in method with exact parameters
                logger.info(f"Attempting sign-in for {phone_number}")
                sign_in_result = await client.sign_in(
                    phone_number=phone_number,
                    phone_code=code_str,
                    phone_code_hash=phone_code_hash
                )
                logger.info(f"Sign-in successful for {phone_number}")

            except SessionPasswordNeeded:
                # 2FA is required
                logger.info(f"Two-factor authentication required for {phone_number}")
                return "2fa_required"

            except (PhoneCodeInvalid, PhoneCodeExpired, PhoneCodeEmpty) as code_error:
                # Specific code-related errors
                logger.error(f"Phone code error for {phone_number}: {code_error}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid authentication code: {str(code_error)}",
                ) from code_error

            except FloodWait as flood_error:
                # Handle rate limiting
                logger.warning(f"Flood wait for {phone_number}: {flood_error.value} seconds")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many requests. Please wait {flood_error.value} seconds.",
                ) from flood_error

            # Get user information after successful sign-in
            me = await client.get_me()
            logger.info(f"User info retrieved for {phone_number}: ID={me.id}, Username={me.username}")

            # Export and save session
            session_string = await client.export_session_string()
            self._sessions[phone_number] = {
                "session_string": session_string,
                "user_id": me.id,
                "username": me.username
            }
            self._save_sessions()

            return "success"

        except Exception as e:
            logger.error(f"Unexpected error during code verification for {phone_number}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Authentication failed: {str(e)}",
            ) from e

    async def verify_password(self, phone_number: str, password: str) -> str:
        """Complete 2FA authentication with comprehensive error handling"""
        if phone_number not in self._clients:
            logger.error(f"No active client found for {phone_number} during password verification")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active authentication session found"
            )

        client = self._clients[phone_number]
        try:
            # Check password
            logger.info(f"Attempting password verification for {phone_number}")
            await client.check_password(password)

            # Get user information
            me = await client.get_me()
            logger.info(f"Password verified for {phone_number}: ID={me.id}, Username={me.username}")

            # Export session
            session_string = await client.export_session_string()

            # Save session
            self._sessions[phone_number] = {
                "session_string": session_string,
                "user_id": me.id,
                "username": me.username
            }
            self._save_sessions()

            return "success"

        except FloodWait as flood_error:
            # Handle rate limiting
            logger.warning(f"Flood wait during password verification for {phone_number}: {flood_error.value} seconds")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many password attempts. Please wait {flood_error.value} seconds.",
            ) from flood_error

        except Exception as e:
            logger.error(f"Error during password verification for {phone_number}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Two-factor authentication failed",
            ) from e

    async def get_account_info(self, phone_number: str, api_id: int, api_hash: str) -> Optional[dict]:
        """Get account information"""
        session = self._sessions.get(phone_number)
        if not session or not session.get("session_string"):
            return None

        try:
            client = await self._create_client(phone_number, api_id, api_hash, session["session_string"])
            with contextlib.suppress(ConnectionError):
                await client.connect()
            me = await client.get_me()
            await client.disconnect()

            return {
                "phone_number": phone_number,
                "user_id": me.id,
                "username": me.username
            }
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None

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

        # Clean up all clients
        await self._cleanup_client(phone_number)

        # Remove session data
        del self._sessions[phone_number]
        self._save_sessions()

        return {"message": "Session removed successfully"}

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup all clients"""
        cleanup_tasks = []
        for phone in list(self._clients.keys()):
            cleanup_tasks.append(self._cleanup_client(phone))
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks)

# Global session manager instance
session_manager = SessionManager()
