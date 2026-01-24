"""
Name: In-Memory Conversation Repository

Responsibilities:
  - Store conversation messages in memory
  - Enforce a max message history per conversation
  - Provide simple lookup by conversation ID
"""

from collections import deque
from threading import Lock
from typing import Deque, Dict, List, Optional
from uuid import uuid4

from ...domain.entities import ConversationMessage
from ...domain.repositories import ConversationRepository


class InMemoryConversationRepository(ConversationRepository):
    """
    R: Thread-safe in-memory conversation repository.
    """

    def __init__(self, max_messages: int = 12):
        self._max_messages = max_messages
        self._lock = Lock()
        self._conversations: Dict[str, Deque[ConversationMessage]] = {}

    def create_conversation(self) -> str:
        conversation_id = str(uuid4())
        with self._lock:
            self._conversations[conversation_id] = deque(maxlen=self._max_messages)
        return conversation_id

    def conversation_exists(self, conversation_id: str) -> bool:
        with self._lock:
            return conversation_id in self._conversations

    def append_message(
        self, conversation_id: str, message: ConversationMessage
    ) -> None:
        with self._lock:
            if conversation_id not in self._conversations:
                self._conversations[conversation_id] = deque(maxlen=self._max_messages)
            self._conversations[conversation_id].append(message)

    def get_messages(
        self, conversation_id: str, limit: Optional[int] = None
    ) -> List[ConversationMessage]:
        with self._lock:
            messages = list(self._conversations.get(conversation_id, []))
        if limit is None or limit <= 0:
            return messages
        return messages[-limit:]
