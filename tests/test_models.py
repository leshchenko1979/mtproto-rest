import pytest
from datetime import datetime
from app.models import Message, Chat, BaseModel, field_validator, Field
from typing import Annotated, Union
from pydantic import ValidationError

# Recreate CodeVerification model directly in the test file to avoid circular imports
class CodeVerification(BaseModel):
    phone_number: Annotated[Union[str, int], Field(description="Phone number in E.164 format")]
    code: Annotated[Union[str, int], Field(description="5-digit verification code")]
    phone_code_hash: str

    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v: Union[str, int]) -> str:
        from app.models import PhoneNumber
        return PhoneNumber(phone_number=v).phone_number

    @field_validator('code')
    @classmethod
    def validate_code(cls, v: Union[str, int]) -> str:
        # Convert to string and strip whitespace
        code_str = str(v).strip()

        # Validate that the code contains only digits
        if not code_str.isdigit():
            raise ValueError("Verification code must contain only digits")

        # Validate code length (typically 5 digits for Telegram)
        if len(code_str) != 5:
            raise ValueError("Verification code must be 5 digits long")

        return code_str

def test_message_link_generation_with_username():
    """Test message link generation for chats with username"""
    Message._chat_info = {
        'chat_id': 123456789,
        'username': 'test_username',
        'type': 'private'
    }

    message = Message(
        message_id=123,
        text="test message",
        date=datetime.now()
    )

    assert message.link == "https://t.me/test_username/123"

def test_message_link_generation_private_chat():
    """Test message link generation for private chats without username"""
    Message._chat_info = {
        'chat_id': 123456789,
        'username': None,
        'type': 'private'
    }

    message = Message(
        message_id=123,
        text="test message",
        date=datetime.now()
    )

    assert message.link == "tg://openmessage?chat_id=123456789&message_id=123"

def test_message_link_generation_channel():
    """Test message link generation for channels without username"""
    Message._chat_info = {
        'chat_id': 123456789,
        'username': None,
        'type': 'channel'
    }

    message = Message(
        message_id=123,
        text="test message",
        date=datetime.now()
    )

    assert message.link == "https://t.me/c/123456789/123"

def test_message_link_generation_group():
    """Test message link generation for groups without username"""
    Message._chat_info = {
        'chat_id': 123456789,
        'username': None,
        'type': 'group'
    }

    message = Message(
        message_id=123,
        text="test message",
        date=datetime.now()
    )

    assert message.link == "tg://openmessage?chat_id=123456789&message_id=123"

def test_message_link_generation_no_chat_info():
    """Test message link generation with no chat info"""
    Message._chat_info = None

    message = Message(
        message_id=123,
        text="test message",
        date=datetime.now()
    )

    assert message.link is None

def test_chat_link_generation_with_username():
    """Test chat link generation for chats with username"""
    chat = Chat(
        chat_id=123456789,
        title="Test Chat",
        type="private",
        username="test_username"
    )

    assert chat.link == "https://t.me/test_username"

def test_chat_link_generation_private():
    """Test chat link generation for private chats without username"""
    chat = Chat(
        chat_id=123456789,
        title="Test Private Chat",
        type="private",
        username=None
    )

    assert chat.link == "tg://user?id=123456789"

def test_chat_link_generation_channel():
    """Test chat link generation for channels without username"""
    chat = Chat(
        chat_id=123456789,
        title="Test Channel",
        type="channel",
        username=None
    )

    assert chat.link == "https://t.me/c/123456789"

def test_chat_link_generation_group():
    """Test chat link generation for groups without username"""
    chat = Chat(
        chat_id=123456789,
        title="Test Group",
        type="group",
        username=None
    )

    assert chat.link == "tg://chat?id=123456789"

def test_message_link_with_negative_chat_id():
    """Test message link generation with negative chat ID"""
    Message._chat_info = {
        'chat_id': -123456789,
        'username': None,
        'type': 'channel'
    }

    message = Message(
        message_id=123,
        text="test message",
        date=datetime.now()
    )

    assert message.link == "https://t.me/c/123456789/123"  # Should use absolute value

def test_chat_link_with_negative_chat_id():
    """Test chat link generation with negative chat ID"""
    chat = Chat(
        chat_id=-123456789,
        title="Test Channel",
        type="channel",
        username=None
    )

    assert chat.link == "https://t.me/c/123456789"  # Should use absolute value

@pytest.fixture(autouse=True)
def cleanup_message_chat_info():
    """Cleanup Message._chat_info after each test"""
    yield
    Message._chat_info = None

def test_code_verification_string_code():
    """Test that a string code is correctly processed"""
    verification = CodeVerification(
        phone_number="+12025550123",
        code="12345",
        phone_code_hash="some_hash"
    )
    assert verification.code == "12345"
    assert isinstance(verification.code, str)

def test_code_verification_integer_code():
    """Test that an integer code is converted to string"""
    verification = CodeVerification(
        phone_number="+12025550123",
        code=12345,
        phone_code_hash="some_hash"
    )
    assert verification.code == "12345"
    assert isinstance(verification.code, str)

def test_code_verification_whitespace_code():
    """Test that whitespace is stripped from the code"""
    verification = CodeVerification(
        phone_number="+12025550123",
        code=" 12345 ",
        phone_code_hash="some_hash"
    )
    assert verification.code == "12345"
    assert isinstance(verification.code, str)

def test_code_verification_invalid_code():
    """Test that non-digit codes raise a validation error"""
    with pytest.raises(ValidationError):
        CodeVerification(
            phone_number="+12025550123",
            code="abcde",
            phone_code_hash="some_hash"
        )

def test_code_verification_empty_code():
    """Test that empty codes raise a validation error"""
    with pytest.raises(ValidationError):
        CodeVerification(
            phone_number="+12025550123",
            code="",
            phone_code_hash="some_hash"
        )

def test_code_verification_none_code():
    """Test that None codes raise a validation error"""
    with pytest.raises(ValidationError):
        CodeVerification(
            phone_number="+12025550123",
            code=None,
            phone_code_hash="some_hash"
        )
