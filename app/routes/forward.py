import contextlib
from fastapi import APIRouter, HTTPException, status
from typing import Optional, List, Union, Dict
from pydantic import BaseModel, Field, field_validator
from app.session_manager import session_manager
from app.main import settings
from app.models import PhoneNumber
from telethon import TelegramClient
from telethon.tl.types import InputPeerChannel, InputPeerUser, InputPeerChat
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

@router.post("/")
async def forward_messages(request: ForwardRequest):
    """Forward messages between chats"""
    try:
        client = await session_manager.get_client(
            request.source_phone,
            settings.API_ID,
            settings.API_HASH
        )

        # Get source chat entity
        try:
            source_entity = await client.get_entity(request.source_chat)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source chat not found: {str(e)}"
            )

        # Get destination chat entity
        try:
            dest_entity = await client.get_entity(request.destination_chat)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Destination chat not found: {str(e)}"
            )

        # Handle message links if provided
        if request.message_links:
            message_ids = []
            for link in request.message_links:
                try:
                    link_info = ForwardRequest.validate_telegram_link(link)
                    message_ids.append(link_info['message_id'])
                except ValueError as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=str(e)
                    )
            request.message_ids = message_ids

        if not request.message_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No message IDs provided"
            )

        # Forward messages
        forwarded = await client.forward_messages(
            entity=dest_entity,
            messages=request.message_ids,
            from_peer=source_entity,
            silent=request.silent,
            noforwards=request.prevent_further_forwards
        )

        # Handle caption removal if requested
        if request.remove_captions and forwarded:
            if not isinstance(forwarded, list):
                forwarded = [forwarded]

            for msg in forwarded:
                if msg.media:
                    await client.edit_message(
                        dest_entity,
                        msg.id,
                        caption=""
                    )

        return {
            "status": "success",
            "message": f"Successfully forwarded {len(request.message_ids)} messages"
        }

    except Exception as e:
        logger.error(f"Error forwarding messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to forward messages: {str(e)}"
        )
