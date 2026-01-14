"""
Name: Conversation Helpers

Responsibilities:
  - Resolve conversation IDs for multi-turn chat
  - Format conversation history into a query string for the LLM

Collaborators:
  - domain.entities.ConversationMessage
  - domain.repositories.ConversationRepository
"""

from typing import Iterable, Optional

from ..domain.entities import ConversationMessage
from ..domain.repositories import ConversationRepository


def resolve_conversation_id(
    repository: ConversationRepository, conversation_id: Optional[str]
) -> str:
    """R: Ensure a valid conversation ID exists."""
    if conversation_id and repository.conversation_exists(conversation_id):
        return conversation_id
    return repository.create_conversation()


def format_conversation_query(
    history: Iterable[ConversationMessage], current_query: str
) -> str:
    """
    R: Format conversation history and current query into a single prompt input.
    """
    history_list = list(history)
    if not history_list:
        return current_query

    lines = ["Historial de conversacion:"]
    for message in history_list:
        role = "Usuario" if message.role == "user" else "Asistente"
        lines.append(f"{role}: {message.content}")
    lines.append(f"Pregunta actual: {current_query}")
    return "\n".join(lines)
