from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional, Annotated, List
from pydantic import BaseModel, Field
from app.session_manager import session_manager
from app.models import Contact, Chat, PhoneNumber, ContactsSearchResponse, ChatsSearchResponse, Message
from app.main import settings
import logging
import logfire
from telethon.tl.functions.messages import SearchGlobalRequest
from telethon.tl.types import InputMessagesFilterEmpty, InputPeerEmpty

# Get logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])

class Contact(BaseModel):
    """Contact information"""
    user_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    phone_number: Optional[str] = None

@router.get("/contacts/{phone_number}")
async def search_contacts(phone_number: str) -> List[Contact]:
    """Search contacts for a given account"""
    source_client = None
    try:
        # Validate phone number using the model
        validated_phone = PhoneNumber(phone_number=phone_number).phone_number

        # Get client
        source_client = await session_manager.get_client(validated_phone, settings.API_ID, settings.API_HASH)

        # Get contacts
        contacts = []
        async for contact in source_client.iter_contacts():
            contacts.append(Contact(
                user_id=contact.id,
                first_name=contact.first_name,
                last_name=contact.last_name,
                username=contact.username,
                phone_number=contact.phone
            ))

        return contacts

    except Exception as e:
        logger.error(f"Error searching contacts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search contacts: {str(e)}"
        )
    finally:
        if source_client:
            await session_manager._cleanup_client(validated_phone)

class Message(BaseModel):
    """Message information"""
    message_id: int
    chat_id: int
    text: Optional[str] = None
    date: Optional[str] = None
    from_user: Optional[int] = None

@router.get("/messages/{phone_number}")
@logfire.instrument()
async def search_messages(
    phone_number: str,
    query: str,
    limit: int = 100
) -> List[Message]:
    """Search messages globally for a given account"""
    source_client = None
    try:
        # Validate phone number using the model
        validated_phone = PhoneNumber(phone_number=phone_number).phone_number

        # Get client
        source_client = await session_manager.get_client(validated_phone, settings.API_ID, settings.API_HASH)

        # Search messages
        messages = []
        async for dialog in source_client.iter_dialogs():
            async for message in source_client.iter_messages(dialog, search=query, limit=limit):
                if message and message.text:  # Only include text messages
                    messages.append(Message(
                        message_id=message.id,
                        chat_id=dialog.id,
                        text=message.text,
                        date=str(message.date) if message.date else None,
                        from_user=message.from_id.user_id if message.from_id else None
                    ))
                    if len(messages) >= limit:
                        break
            if len(messages) >= limit:
                break

        return messages[:limit]

    except Exception as e:
        logger.error(f"Error searching messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search messages: {str(e)}"
        )
    finally:
        if source_client:
            await session_manager._cleanup_client(validated_phone)

@router.get("/chats", response_model=ChatsSearchResponse)
async def search_chats(
    phone_number: Annotated[str, Query(description="Phone number in E.164 format")],
    query: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=100)
):
    """Search chats globally using Telegram's native global search"""
    source_client = None
    try:
        # Validate phone number using the model
        validated_phone = PhoneNumber(phone_number=phone_number).phone_number
        source_client = await session_manager.get_client(validated_phone, settings.API_ID, settings.API_HASH)

        logger.info("Starting global chat search", extra={
            "query": query,
            "phone_number": validated_phone,
            "limit": limit
        })

        chats_dict = {}  # Use dict to avoid duplicates, with chat_id as key

        # Create the search request with proper input types
        request = SearchGlobalRequest(
            q=query,
            filter=InputMessagesFilterEmpty(),
            min_date=None,
            max_date=None,
            offset_rate=0,
            offset_peer=InputPeerEmpty(),  # Use proper input peer type
            offset_id=0,
            limit=limit
        )

        # Use Telegram's native global search
        result = await source_client(request)

        # Process search results
        for message in result.messages:
            if not message or not message.peer_id:
                continue

            # Get full chat information
            chat = await source_client.get_entity(message.peer_id)
            if not chat:
                continue

            chat_id = chat.id

            # Determine chat type
            chat_type = "private" if hasattr(chat, 'first_name') else (
                "channel" if getattr(chat, 'broadcast', False) else "group"
            )

            # Get chat title
            if chat_type == "private":
                chat_title = f"{getattr(chat, 'first_name', '')} {getattr(chat, 'last_name', '')}".strip()
            else:
                chat_title = getattr(chat, 'title', None)

            if not chat_title:
                continue

            # Create or update Chat object
            if chat_id not in chats_dict:
                chat_obj = Chat(
                    chat_id=chat_id,
                    title=chat_title,
                    type=chat_type,
                    username=getattr(chat, "username", None),
                    members_count=getattr(chat, "participants_count", None),
                    last_message_date=message.date,
                    matching_messages=[]
                )
                chats_dict[chat_id] = chat_obj

            # Set chat info for message link generation
            Message._chat_info = {
                'chat_id': chat_id,
                'username': getattr(chat, "username", None),
                'type': chat_type
            }

            # Add matching message
            matching_message = Message(
                message_id=message.id,
                chat_id=chat_id,
                text=getattr(message, 'message', None) or getattr(message, 'caption', None),
                date=str(message.date) if message.date else None,
                from_user=message.from_id.user_id if message.from_id else None
            )
            chats_dict[chat_id].matching_messages.append(matching_message)

        result_chats = list(chats_dict.values())
        logger.info("Global chat search completed", extra={
            "query": query,
            "matches_found": len(result_chats),
            "phone_number": validated_phone
        })
        return ChatsSearchResponse(chats=result_chats)

    except Exception as e:
        logger.error("Error in chat search", extra={
            "error": str(e),
            "error_type": type(e).__name__,
            "query": query,
            "phone_number": validated_phone
        }, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search chats: {str(e)}"
        )
    finally:
        if source_client:
            await session_manager._cleanup_client(validated_phone)
