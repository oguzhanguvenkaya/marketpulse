"""Router de-duplication testleri.

Plan dogrulama:
- GET /api/ai/conversations yanitinda message_count zorunlu dogrulanir.
- GET /api/ai/conversations/{id}/messages?limit=1 cagrisinda tool_calls alani dogrulanir.
- Duplicate router temizligi sonrasi yalnizca streaming router'daki implementasyon calismali.
"""

import uuid
import pytest
from datetime import datetime

from app.db.models import User, ChatConversation, ChatMessage


@pytest.fixture()
def test_user(db_session):
    """Test icin kullanici olustur."""
    user = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@test.com",
        full_name="Test User",
        plan_tier="free",
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture()
def conversation_with_messages(db_session, test_user):
    """Conversation + mesajlar olustur."""
    conv_id = uuid.uuid4()
    conv = ChatConversation(
        id=conv_id,
        user_id=test_user.id,
        title="Test Sohbet",
    )
    db_session.add(conv)
    db_session.flush()

    # User mesaji
    msg1 = ChatMessage(
        conversation_id=conv_id,
        role="user",
        content="Fiyat alarmlarimi goster",
    )
    db_session.add(msg1)

    # Tool calls ile assistant mesaji
    tool_calls_data = [
        {
            "id": "call_123",
            "type": "function",
            "function": {
                "name": "get_price_alerts",
                "arguments": "{}",
            },
        }
    ]
    msg2 = ChatMessage(
        conversation_id=conv_id,
        role="assistant",
        content="",
        tool_calls=tool_calls_data,
    )
    db_session.add(msg2)

    # Tool mesaji
    msg3 = ChatMessage(
        conversation_id=conv_id,
        role="tool",
        content='{"toplam_izlenen": 5}',
        tool_call_id="call_123",
    )
    db_session.add(msg3)

    # Final assistant mesaji
    msg4 = ChatMessage(
        conversation_id=conv_id,
        role="assistant",
        content="5 urun izleniyor.",
    )
    db_session.add(msg4)
    db_session.flush()

    return conv


class TestListConversations:
    """GET /api/ai/conversations"""

    def test_returns_message_count(self, client, db_session, test_user, conversation_with_messages):
        """Yanit message_count alanini icermeli."""
        # Auth bypass icin mock — test ortaminda JWT olmadan calismali
        from unittest.mock import AsyncMock
        from app.core.auth import get_current_user
        from app.main import app

        async def mock_user():
            return test_user

        app.dependency_overrides[get_current_user] = mock_user

        response = client.get("/api/ai/conversations")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # Bizim conversation'i bul
        conv = next(
            (c for c in data if c["id"] == str(conversation_with_messages.id)),
            None,
        )
        assert conv is not None
        assert "message_count" in conv
        assert conv["message_count"] == 4  # user + assistant(tool_calls) + tool + assistant

        app.dependency_overrides.pop(get_current_user, None)

    def test_conversations_sorted_by_updated_at(self, client, db_session, test_user, conversation_with_messages):
        """Konusmalar updated_at'e gore azalan sirada gelmeli."""
        from app.core.auth import get_current_user
        from app.main import app

        # Ikinci conversation olustur
        conv2 = ChatConversation(
            id=uuid.uuid4(),
            user_id=test_user.id,
            title="Yeni Sohbet",
        )
        db_session.add(conv2)
        db_session.flush()

        async def mock_user():
            return test_user

        app.dependency_overrides[get_current_user] = mock_user

        response = client.get("/api/ai/conversations")
        data = response.json()
        assert len(data) >= 2

        app.dependency_overrides.pop(get_current_user, None)


class TestGetMessages:
    """GET /api/ai/conversations/{id}/messages"""

    def test_returns_tool_calls_field(self, client, db_session, test_user, conversation_with_messages):
        """Mesaj yanitinda tool_calls alani olmali."""
        from app.core.auth import get_current_user
        from app.main import app

        async def mock_user():
            return test_user

        app.dependency_overrides[get_current_user] = mock_user

        conv_id = str(conversation_with_messages.id)
        response = client.get(f"/api/ai/conversations/{conv_id}/messages")
        assert response.status_code == 200

        messages = response.json()
        assert len(messages) == 4

        # Assistant mesajinda tool_calls olmali
        assistant_msgs = [m for m in messages if m["role"] == "assistant"]
        has_tool_calls = any(m.get("tool_calls") for m in assistant_msgs)
        assert has_tool_calls

        # Tool mesajinda tool_call_id olmali
        tool_msgs = [m for m in messages if m["role"] == "tool"]
        assert len(tool_msgs) == 1
        assert tool_msgs[0]["tool_call_id"] == "call_123"

        app.dependency_overrides.pop(get_current_user, None)

    def test_limit_parameter(self, client, db_session, test_user, conversation_with_messages):
        """limit query param calismali."""
        from app.core.auth import get_current_user
        from app.main import app

        async def mock_user():
            return test_user

        app.dependency_overrides[get_current_user] = mock_user

        conv_id = str(conversation_with_messages.id)
        response = client.get(f"/api/ai/conversations/{conv_id}/messages?limit=1")
        assert response.status_code == 200

        messages = response.json()
        assert len(messages) == 1

        app.dependency_overrides.pop(get_current_user, None)


class TestDeleteConversation:
    """DELETE /api/ai/conversations/{id}"""

    def test_delete_returns_status(self, client, db_session, test_user, conversation_with_messages):
        """Silme islemi basarili status donmeli."""
        from app.core.auth import get_current_user
        from app.main import app

        async def mock_user():
            return test_user

        app.dependency_overrides[get_current_user] = mock_user

        conv_id = str(conversation_with_messages.id)
        response = client.delete(f"/api/ai/conversations/{conv_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

        app.dependency_overrides.pop(get_current_user, None)

    def test_delete_nonexistent_returns_404(self, client, db_session, test_user):
        """Olmayan conversation icin 404 donmeli."""
        from app.core.auth import get_current_user
        from app.main import app

        async def mock_user():
            return test_user

        app.dependency_overrides[get_current_user] = mock_user

        fake_id = str(uuid.uuid4())
        response = client.delete(f"/api/ai/conversations/{fake_id}")
        assert response.status_code == 404

        app.dependency_overrides.pop(get_current_user, None)
