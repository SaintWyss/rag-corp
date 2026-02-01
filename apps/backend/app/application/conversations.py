"""
Name: Conversation Utilities

Responsibilities:
  - Provide helpers for conversation management
  - Format conversation history for LLM queries
  - Manage conversation ID resolution

Collaborators:
  - domain.repositories: ConversationRepository
  - domain.entities: ConversationMessage

Constraints:
  - Must be stateless and pure functions where possible
  - No side effects except for ID resolution
"""

from typing import List
from uuid import uuid4

from ..domain.entities import ConversationMessage
from ..domain.repositories import ConversationRepository


def resolve_conversation_id(
    repository: ConversationRepository,
    conversation_id: str | None,
) -> str:
    """
    Resolve or create a conversation ID.

    If conversation_id is provided and valid, return it.
    Otherwise, create a new conversation and return its ID.

    Args:
        repository: Conversation repository instance
        conversation_id: Optional existing conversation ID

    Returns:
        A valid conversation ID (existing or newly created)
    """
    if conversation_id:
        # Validate that the conversation exists
        try:
            repository.get_messages(conversation_id, limit=1)
            # If we can get messages (even empty list), the ID is valid
            return conversation_id
        except Exception:
            # If the conversation doesn't exist, create a new one
            pass

    # Create a new conversation
    new_id = str(uuid4())
    repository.save_conversation(new_id, [])
    return new_id


def format_conversation_query(
    history: List[ConversationMessage],
    current_query: str,
) -> str:
    """
    Format conversation history and current query for LLM consumption.

    Combines previous messages with the current query to maintain
    conversational context for the LLM.

    Args:
        history: List of previous conversation messages
        current_query: The current user query

    Returns:
        Formatted query string with context
    """
    if not history:
        return current_query

    # Build context from history
    context_parts = []
    for msg in history:
        role_label = "Usuario" if msg.role == "user" else "Asistente"
        context_parts.append(f"{role_label}: {msg.content}")

    # Add the current query
    context_parts.append(f"Usuario: {current_query}")

    # Join with newlines
    return "\n".join(context_parts)


__all__ = [
    "resolve_conversation_id",
    "format_conversation_query",
]
