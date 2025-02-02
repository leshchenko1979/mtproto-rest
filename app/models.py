from typing import Optional, Union, Literal, List
from pydantic import BaseModel, field_validator, Field
from datetime import datetime
import re

# E.164 phone number regex pattern
PHONE_PATTERN = re.compile(r'^\+?[1-9]\d{1,14}$')

class PhoneNumber(BaseModel):
    """Base model for phone number validation"""
    phone_number: Union[str, int] = Field(..., description="Phone number in E.164 format")

    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v: Union[str, int]) -> str:
        """Validate and normalize phone number to E.164 format"""
        if isinstance(v, int):
            v = str(v)
        v = re.sub(r'[\s-]', '', v)
        if not PHONE_PATTERN.match(v):
            raise ValueError('Invalid phone number format. Must be in E.164 format')
        return '+' + v.lstrip('+')

class Contact(BaseModel):
    """Telegram contact information"""
    user_id: int = Field(..., description="Unique Telegram user ID")
    first_name: Optional[str] = Field(None, description="Contact's first name")
    last_name: Optional[str] = Field(None, description="Contact's last name")
    username: Optional[str] = Field(None, description="Contact's Telegram username")
    phone_number: Optional[str] = Field(None, description="Contact's phone number")
    link: str = Field("", description="Link to contact's Telegram profile")

    @field_validator('link', mode='before')
    @classmethod
    def generate_contact_link(cls, v: str, values: dict) -> str:
        """Generate Telegram link for the contact"""
        if 'username' in values and values['username']:
            return f"https://t.me/{values['username']}"
        return f"tg://user?id={values['user_id']}"

    @field_validator('phone_number')
    @classmethod
    def validate_optional_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone number if present"""
        if v:
            if not PHONE_PATTERN.match(v):
                raise ValueError('Invalid phone number format')
            return '+' + v.lstrip('+')
        return v

class Message(BaseModel):
    message_id: int
    text: Optional[str] = None
    date: Optional[datetime] = None
    from_user: Optional[int] = None
    link: Optional[str] = None
    _chat_info: Optional[dict] = None  # Class variable to store chat info

    def __init__(self, **data):
        super().__init__(**data)
        # Generate link after initialization
        self.link = self.generate_message_link(self.link, self.model_dump())

    @classmethod
    def generate_message_link(cls, v: Optional[str], values: dict) -> Optional[str]:
        """Generate Telegram link for the message"""
        if not values or not cls._chat_info or not values.get('message_id'):
            return None

        chat = cls._chat_info
        message_id = values['message_id']
        chat_id = chat.get('chat_id')
        username = chat.get('username')
        chat_type = chat.get('type')

        # First try username-based link for public chats/channels
        if username:
            return f"https://t.me/{username}/{message_id}"

        # Handle private chats and channels without username
        if not chat_id:
            return None

        if chat_type == 'channel':
            # For channels without username, use c/{chat_id} format
            return f"https://t.me/c/{abs(chat_id)}/{message_id}"
        elif chat_type == 'private':
            # For private chats, use openmessage format
            return f"tg://openmessage?chat_id={chat_id}&message_id={message_id}"
        else:
            # For groups, use standard format
            return f"tg://openmessage?chat_id={chat_id}&message_id={message_id}"

class Chat(BaseModel):
    """Telegram chat information"""
    chat_id: int = Field(..., description="Unique Telegram chat ID")
    title: Optional[str] = Field(None, description="Chat title")
    type: Literal['private', 'group', 'channel'] = Field(..., description="Chat type")
    username: Optional[str] = Field(None, description="Chat username")
    members_count: Optional[int] = Field(None, ge=0, description="Number of members in chat")
    last_message_date: Optional[datetime] = Field(None, description="Date of last message")
    matching_messages: List[Message] = Field(default_factory=list, description="List of matching messages in this chat")
    link: str = Field("", description="Link to the chat")

    def __init__(self, **data):
        super().__init__(**data)
        # Generate link after initialization
        self.link = self.generate_chat_link(self.link, self.model_dump())

    @classmethod
    def generate_chat_link(cls, v: str, values: dict) -> str:
        """Generate Telegram link for the chat"""
        if not values:
            return ""

        chat_id = values.get('chat_id')
        username = values.get('username')
        chat_type = values.get('type')

        # First try username-based link for public chats/channels
        if username:
            return f"https://t.me/{username}"

        # Handle chats without username
        if not chat_id:
            return ""

        if chat_type == 'channel':
            # For channels without username, use c/{chat_id} format
            return f"https://t.me/c/{abs(chat_id)}"
        elif chat_type == 'private':
            # For private chats, use user format
            return f"tg://user?id={chat_id}"
        else:
            # For groups, use chat format
            return f"tg://chat?id={chat_id}"

class SessionInfo(BaseModel):
    """Telegram session information"""
    phone_number: str = Field(..., description="Phone number in E.164 format")
    session_string: str = Field(..., description="Pyrogram session string")
    user_id: int = Field(..., description="Telegram user ID")
    username: Optional[str] = Field(None, description="Telegram username")

    @field_validator('phone_number')
    @classmethod
    def validate_session_phone(cls, v: str) -> str:
        """Validate session phone number"""
        if not PHONE_PATTERN.match(v):
            raise ValueError('Invalid phone number format')
        return '+' + v.lstrip('+')

class SearchResponse(BaseModel):
    """Base search response with pagination info"""
    total_count: int = Field(..., description="Total number of items available")
    returned_count: int = Field(..., description="Number of items returned in this response")
    has_more: bool = Field(..., description="Whether there are more items available")

class ContactsSearchResponse(BaseModel):
    """Response model for contacts search"""
    contacts: List[Contact]

class ChatsSearchResponse(BaseModel):
    """Response model for chats search"""
    chats: List[Chat]
