import contextlib
from fastapi import APIRouter, HTTPException, status
from typing import Optional, List, Union, Dict
from pydantic import BaseModel, Field, field_validator
from app.session_manager import session_manager
from app.main import settings
from app.models import PhoneNumber
from pyrogram import Client
from pyrogram.raw import functions, types
import logging
import random
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/forward", tags=["forward"])

class ForwardRequest(BaseModel):
    """Request model for forwarding messages"""
    source_phone: Union[str, int] = Field(..., description="Phone number of the source account")
    source_chat: Union[int, str, List[Union[int, str]]] = Field(..., description="Source chat username or public message links")
    destination_chat: Union[int, str] = Field(..., description="Destination chat username")
    message_ids: Optional[List[int]] = Field(None, description="Specific message IDs to forward")
    message_links: Optional[List[str]] = Field(None, description="Public Telegram message links to forward")
    remove_sender_info: bool = Field(default=False, description="Remove sender information when forwarding")
    remove_captions: bool = Field(default=False, description="Remove media captions")
    prevent_further_forwards: bool = Field(default=False, description="Prevent further forwarding of messages")
    silent: bool = Field(default=False, description="Send without triggering notifications")

    @field_validator('source_phone')
    @classmethod
    def validate_phone_number(cls, v: Union[str, int]) -> str:
        return PhoneNumber(phone_number=v).phone_number

    @staticmethod
    def validate_telegram_link(link: str) -> Dict[str, Union[str, int]]:
        """Parse Telegram public message link"""
        link = link.lstrip('@')

        if link.startswith('https://t.me/'):
            path_parts = urlparse(link).path.strip('/').split('/')
        else:
            path_parts = link.split('/')

        if len(path_parts) == 2:
            with contextlib.suppress(ValueError):
                return {
                    'username': path_parts[0],
                    'message_id': int(path_parts[1])
                }
        raise ValueError(f"Invalid Telegram message link: {link}")

async def safe_join_chat(client: Client, chat: str) -> None:
    """Safely join a chat without raising exceptions"""
    try:
        await client.join_chat(chat)
    except Exception as e:
        logger.warning(f"Failed to join chat {chat}: {e}")

@router.post("/messages", status_code=status.HTTP_200_OK)
async def forward_messages(request: ForwardRequest):
    """Forward messages with forced chat joining"""
    source_client = None
    try:
        source_client = await session_manager.get_client(
            request.source_phone, settings.API_ID, settings.API_HASH
        )

        if not request.message_links and not request.message_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No messages to forward provided"
            )

        # Get source chat from either source_chat or first message link
        source_chat = request.source_chat
        message_ids = list(request.message_ids or [])

        # Add message IDs from links if any
        if request.message_links:
            for link in request.message_links:
                try:
                    parsed = ForwardRequest.validate_telegram_link(link)
                    # If we got source_chat from source_chat, verify link is from same chat
                    if isinstance(source_chat, str):
                        chat_username = source_chat.lstrip('@')
                        if parsed['username'] != chat_username:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail="All messages must be from the same chat"
                            )
                    else:
                        source_chat = parsed['username']
                    message_ids.append(parsed['message_id'])
                except ValueError as e:
                    logger.error(f"Invalid link format: {link}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
                    ) from e

        # Join source and destination chats
        await safe_join_chat(source_client, source_chat)
        await safe_join_chat(source_client, request.destination_chat)

        # Resolve peers
        source_peer = await source_client.resolve_peer(source_chat)
        destination_peer = await source_client.resolve_peer(request.destination_chat)

        # Generate random IDs for all messages
        random_ids = [random.randint(1, 2**31 - 1) for _ in message_ids]

        # Forward all messages in a single call
        result = await source_client.invoke(
            functions.messages.ForwardMessages(
                from_peer=source_peer,
                id=message_ids,
                random_id=random_ids,
                to_peer=destination_peer,
                drop_author=request.remove_sender_info,
                drop_media_captions=request.remove_captions,
                noforwards=request.prevent_further_forwards,
                silent=request.silent
            )
        )

        # Extract forwarded message IDs
        forwarded_messages = []
        if hasattr(result, 'updates'):
            forwarded_messages = [
                update.id
                for update in result.updates
                if hasattr(update, 'id')
            ]

        if not forwarded_messages:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No messages were forwarded successfully"
            )

        return {
            "status": "success",
            "forwarded_message_ids": forwarded_messages
        }

    except Exception as e:
        logger.error(f"Forward operation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e
    finally:
        if source_client:
            await session_manager._cleanup_client(request.source_phone)
