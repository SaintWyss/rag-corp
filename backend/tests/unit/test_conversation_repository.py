"""
Name: Conversation Repository Unit Tests

Responsibilities:
  - Validate in-memory conversation storage behavior
  - Ensure message limits are enforced
"""

import pytest

from app.domain.entities import ConversationMessage
from app.infrastructure.repositories import InMemoryConversationRepository


@pytest.mark.unit
class TestInMemoryConversationRepository:
    def test_create_and_append_messages(self):
        repo = InMemoryConversationRepository(max_messages=3)
        conversation_id = repo.create_conversation()

        assert repo.conversation_exists(conversation_id) is True

        repo.append_message(
            conversation_id,
            ConversationMessage(role="user", content="Hola"),
        )
        messages = repo.get_messages(conversation_id)

        assert len(messages) == 1
        assert messages[0].role == "user"
        assert messages[0].content == "Hola"

    def test_append_creates_missing_conversation(self):
        repo = InMemoryConversationRepository(max_messages=2)
        conversation_id = "manual-id"

        assert repo.conversation_exists(conversation_id) is False

        repo.append_message(
            conversation_id,
            ConversationMessage(role="assistant", content="Respuesta"),
        )

        assert repo.conversation_exists(conversation_id) is True
        assert len(repo.get_messages(conversation_id)) == 1

    def test_max_messages_are_enforced(self):
        repo = InMemoryConversationRepository(max_messages=2)
        conversation_id = repo.create_conversation()

        repo.append_message(
            conversation_id,
            ConversationMessage(role="user", content="m0"),
        )
        repo.append_message(
            conversation_id,
            ConversationMessage(role="assistant", content="m1"),
        )
        repo.append_message(
            conversation_id,
            ConversationMessage(role="user", content="m2"),
        )

        messages = repo.get_messages(conversation_id)
        assert [msg.content for msg in messages] == ["m1", "m2"]

    def test_limit_returns_last_n_messages(self):
        repo = InMemoryConversationRepository(max_messages=5)
        conversation_id = repo.create_conversation()

        for idx in range(4):
            role = "user" if idx % 2 == 0 else "assistant"
            repo.append_message(
                conversation_id,
                ConversationMessage(role=role, content=f"m{idx}"),
            )

        messages = repo.get_messages(conversation_id, limit=2)
        assert [msg.content for msg in messages] == ["m2", "m3"]
