from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional, Annotated
from app.session_manager import session_manager
from app.models import Contact, Chat, PhoneNumber, ContactsSearchResponse, ChatsSearchResponse, Message
from app.main import settings
import logging

# Get logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])

@router.get("/contacts", response_model=ContactsSearchResponse)
async def search_contacts(
    phone_number: str,
    query: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=100)
):
    """Search contacts"""
    source_client = None
    try:
        # Validate phone number
        validated_phone = PhoneNumber(phone_number=phone_number).phone_number
        source_client = await session_manager.get_client(validated_phone, settings.API_ID, settings.API_HASH)

        contacts = []
        async for contact in source_client.get_contacts():
            if (query.lower() in (contact.first_name or '').lower() or
                query.lower() in (contact.last_name or '').lower() or
                query.lower() in (contact.phone_number or '').lower()):
                contacts.append(Contact(
                    user_id=contact.id,
                    first_name=contact.first_name,
                    last_name=contact.last_name,
                    username=contact.username,
                    phone_number=contact.phone_number
                ))
                if len(contacts) >= limit:
                    break
        return ContactsSearchResponse(contacts=contacts)

    except Exception as e:
        logger.error(f"Error searching contacts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search contacts: {str(e)}"
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
    """Search chats globally"""
    source_client = None
    try:
        # Validate phone number
        validated_phone = PhoneNumber(phone_number=phone_number).phone_number
        source_client = await session_manager.get_client(validated_phone, settings.API_ID, settings.API_HASH)

        logger.info("Starting global chat search", extra={
            "query": query,
            "phone_number": validated_phone,
            "limit": limit
        })

        chats_dict = {}  # Use dict to avoid duplicates, with chat_id as key

        # Search globally with empty filter to get all types of results
        async for message in source_client.search_global(query, limit=limit):
            chat = message.chat
            if not chat:
                continue

            chat_type = "private" if chat.type == "private" else (
                "channel" if chat.type == "channel" else "group"
            )

            # Get chat title, handling None case
            chat_title = getattr(chat, 'title', None)
            if chat_title is None:
                # For private chats, construct title from first/last name
                if chat.type == "private":
                    first_name = getattr(chat, 'first_name', '')
                    last_name = getattr(chat, 'last_name', '')
                    chat_title = f"{first_name} {last_name}".strip()
                if not chat_title:
                    continue

            # Create or get existing Chat object
            if chat.id not in chats_dict:
                chat_obj = Chat(
                    chat_id=chat.id,
                    title=chat_title,
                    type=chat_type,
                    username=getattr(chat, "username", None),
                    members_count=getattr(chat, "members_count", None),
                    last_message_date=message.date if message else None,
                    matching_messages=[]
                )
                chats_dict[chat.id] = chat_obj
            else:
                chat_obj = chats_dict[chat.id]

            # Set chat info for message link generation
            Message._chat_info = {
                'chat_id': chat.id,
                'username': getattr(chat, "username", None),
                'type': chat_type
            }

            # Create and add matching message
            matching_message = Message(
                message_id=message.id,
                text=message.text or message.caption,
                date=message.date,
                from_user=message.from_user.id if message.from_user else None
            )
            chat_obj.matching_messages.append(matching_message)

            if len(chats_dict) >= limit:
                logger.info("Search limit reached", extra={
                    "limit": limit,
                    "query": query
                })
                break

        result_chats = list(chats_dict.values())  # Convert dict values to list
        logger.info("Global chat search completed", extra={
            "query": query,
            "matches_found": len(result_chats),
            "phone_number": validated_phone
        })
        return ChatsSearchResponse(chats=result_chats)

    except AttributeError as e:
        logger.error("Attribute error in chat search", extra={
            "error": str(e),
            "query": query,
            "phone_number": validated_phone
        }, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error accessing chat attributes"
        ) from e
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
