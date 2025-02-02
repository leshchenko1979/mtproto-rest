from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional
from contextlib import asynccontextmanager
from ..auth import get_client, load_sessions_info
from ..models import Contact, Chat, PhoneNumber, ContactsSearchResponse, ChatsSearchResponse, Message
import logging
import traceback
from pyrogram import raw
import os
from datetime import datetime

# Get logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])

@asynccontextmanager
async def telegram_client(phone_number: str):
    """Context manager for handling Telegram client connections"""
    sessions = load_sessions_info()
    if phone_number not in sessions:
        logger.error(f"Session not found for phone number: {phone_number}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found for {phone_number}. Please authenticate first."
        )

    client = None
    try:
        client = await get_client(sessions[phone_number]["session_string"])
        await client.connect()
        yield client
    except Exception as e:
        logger.error(f"Error in telegram_client: {str(e)}\n{traceback.format_exc()}")
        raise
    finally:
        if client:
            try:
                await client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting client: {str(e)}")

@router.get("/contacts")
async def search_contacts(
    phone_number: str = Query(..., description="Phone number in E.164 format"),
    query: str = Query(..., min_length=1),
    limit: Optional[int] = Query(20, ge=1, le=100, description="Maximum number of contacts to return")
) -> ContactsSearchResponse:
    """Search for contacts using raw API methods"""
    try:
        logger.info(f"Starting contact search for query: {query}")
        validated_phone = PhoneNumber(phone_number=phone_number).phone_number

        async with telegram_client(validated_phone) as client:
            contacts = {}  # Use dict for deduplication
            try:
                # First get all contacts
                all_contacts = await client.invoke(
                    raw.functions.contacts.GetContacts(
                        hash=0  # 0 means get all contacts
                    )
                )

                # Filter contacts by query
                query_lower = query.lower()
                for user in all_contacts.users:
                    if len(contacts) >= limit:
                        break
                    if any(
                        value and query_lower in str(value).lower()
                        for value in (
                            user.first_name,
                            user.last_name,
                            user.username,
                            user.phone
                        )
                    ):
                        contacts[user.id] = Contact(
                            user_id=user.id,
                            first_name=user.first_name,
                            last_name=user.last_name,
                            username=user.username,
                            phone_number=user.phone
                        )

                # Also search in global contacts if we haven't reached the limit
                if len(contacts) < limit:
                    remaining_limit = min(20, limit - len(contacts))  # Use smaller of 20 or remaining slots
                    global_contacts = await client.invoke(
                        raw.functions.contacts.Search(
                            q=query,
                            limit=remaining_limit
                        )
                    )

                    # Add global results to contacts dict
                    for user in global_contacts.users:
                        if len(contacts) >= limit:
                            break
                        if user.id not in contacts:
                            contacts[user.id] = Contact(
                                user_id=user.id,
                                first_name=user.first_name,
                                last_name=user.last_name,
                                username=user.username,
                                phone_number=user.phone
                            )

            except Exception as e:
                logger.error(f"Error in contacts search: {str(e)}\n{traceback.format_exc()}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Search failed: {str(e)}"
                )

            result = list(contacts.values())
            logger.info(f"Found {len(result)} unique contacts")
            return ContactsSearchResponse(contacts=result)

    except Exception as e:
        logger.error(f"Error in search_contacts: {str(e)}\n{traceback.format_exc()}")
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/chats")
async def search_chats(
    phone_number: str = Query(..., description="Phone number in E.164 format"),
    query: str = Query(..., min_length=1),
    chat_type: Optional[str] = Query(None, regex="^(private|group|channel|all)$"),
    limit: Optional[int] = Query(20, ge=1, le=100, description="Maximum number of chats to return")
) -> ChatsSearchResponse:
    """Search for chats using global search"""
    try:
        logger.info(f"Starting chat search for query: {query}, type: {chat_type}")
        validated_phone = PhoneNumber(phone_number=phone_number).phone_number

        async with telegram_client(validated_phone) as client:
            chats = {}
            try:
                # Use SearchGlobal with appropriate flags
                if chat_type == "channel":
                    # For channels, we'll filter after getting results
                    results = await client.invoke(
                        raw.functions.messages.SearchGlobal(
                            q=query,
                            filter=raw.types.InputMessagesFilterEmpty(),
                            min_date=0,
                            max_date=0,
                            offset_rate=0,
                            offset_peer=raw.types.InputPeerEmpty(),
                            offset_id=0,
                            limit=limit,
                            folder_id=0
                        )
                    )
                else:
                    # For groups or private chat results
                    results = await client.invoke(
                        raw.functions.messages.SearchGlobal(
                            q=query,
                            filter=raw.types.InputMessagesFilterEmpty(),
                            min_date=0,
                            max_date=0,
                            offset_rate=0,
                            offset_peer=raw.types.InputPeerEmpty(),
                            offset_id=0,
                            limit=limit,
                            folder_id=0
                        )
                    )

                # Process found chats and messages
                messages_by_chat = {}  # Store messages by chat_id
                for message in results.messages:
                    if len(chats) >= limit:
                        break

                    # Get the chat where the message was posted
                    peer_id = message.peer_id
                    chat_id = getattr(peer_id, "channel_id", None) or getattr(peer_id, "chat_id", None) or peer_id.user_id

                    # Find corresponding chat for link generation
                    chat_info = None
                    chat_obj = None
                    for chat in results.chats + results.users:  # Include users in search
                        if chat.id == chat_id:
                            is_broadcast = getattr(chat, "broadcast", False)
                            is_megagroup = getattr(chat, "megagroup", False)
                            is_user = hasattr(chat, "first_name")

                            chat_type_actual = (
                                "channel" if is_broadcast and not is_megagroup
                                else "group" if is_megagroup or getattr(chat, "gigagroup", False)
                                else "private" if is_user
                                else "group"
                            )

                            # For private chats, we only want messages from private conversations
                            if chat_type == "private" and chat_type_actual != "private":
                                continue

                            chat_info = {
                                'chat_id': chat.id,
                                'username': getattr(chat, 'username', None),
                                'type': chat_type_actual
                            }
                            chat_obj = chat
                            break

                    # Set chat info for message link generation
                    Message._chat_info = chat_info

                    if chat_info and (chat_type == "all" or chat_info['type'] == chat_type):
                        # Create message with chat info
                        message_obj = Message(
                            message_id=message.id,
                            text=getattr(message, "message", None),
                            date=datetime.fromtimestamp(message.date) if message.date else None,
                            from_user=getattr(message.from_id, "user_id", None) if hasattr(message, "from_id") else None
                        )

                        # Add chat to results if it's not there yet
                        if chat_obj and chat_id not in chats:
                            chat_title = (
                                getattr(chat_obj, "title", None) or
                                f"{getattr(chat_obj, 'first_name', '')} {getattr(chat_obj, 'last_name', '')}".strip() or
                                None
                            )

                            # Create chat object
                            chat_data = {
                                'chat_id': chat_id,
                                'title': chat_title,
                                'type': chat_type_actual,
                                'username': getattr(chat_obj, "username", None),
                                'matching_messages': [message_obj],  # Initialize with first message
                                'last_message_date': datetime.fromtimestamp(message.date) if message.date else None
                            }

                            chats[chat_id] = Chat(**chat_data)
                        else:
                            # Add message to existing chat's matching_messages
                            chats[chat_id].matching_messages.append(message_obj)
                            # Update last_message_date if this message is newer
                            message_date = datetime.fromtimestamp(message.date) if message.date else None
                            if message_date and (not chats[chat_id].last_message_date or message_date > chats[chat_id].last_message_date):
                                chats[chat_id].last_message_date = message_date

                    Message._chat_info = None

            except Exception as e:
                logger.error(f"Error in global search: {str(e)}\n{traceback.format_exc()}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Search failed: {str(e)}"
                )

            result = list(chats.values())
            logger.info(f"Found {len(result)} unique chats")
            return ChatsSearchResponse(chats=result)

    except Exception as e:
        logger.error(f"Error in search_chats: {str(e)}\n{traceback.format_exc()}")
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
