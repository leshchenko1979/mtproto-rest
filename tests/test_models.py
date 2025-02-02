import pytest
from datetime import datetime
from app.models import Message, Chat

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
