"""
Name: Conversation Helpers (Formatters & Resolvers)

Responsibilities:
  - Resolve conversation IDs for multi-turn chat (create if missing/invalid)
  - Format conversation history into a single query string for the LLM
  - Support strict windowing to avoid blowing up context tokens

Architecture:
  - Clean Architecture / Hexagonal
  - Layer: Application utility
  - Depends on domain ports/entities only (ConversationRepository, ConversationMessage)

Patterns:
  - Factory/Resolver: logic to valid chat IDs
  - Formatter / Template View: transform logic for history -> text
  - Windowing Strategy: simple "last N messages"
"""

from __future__ import annotations

from typing import Iterable, Optional

from ..domain.entities import ConversationMessage
from ..domain.repositories import ConversationRepository


def resolve_conversation_id(
    repository: ConversationRepository,
    conversation_id: str | None,
) -> str:
    """
    R: Ensure a valid conversation ID exists using the repository.
    """
    if conversation_id and repository.conversation_exists(conversation_id):
        return conversation_id
    return repository.create_conversation()


def _role_label(role: str) -> str:
    """R: Map internal roles to Spanish labels for the LLM."""
    role_norm = (role or "").strip().lower()
    if role_norm == "user":
        return "Usuario"
    if role_norm in {"assistant", "model"}:
        return "Asistente"
    if role_norm in {"system", "developer"}:
        return "Sistema"
    return role or "Desconocido"


def format_conversation_query(
    history: Iterable[ConversationMessage],
    current_query: str,
    *,
    max_messages: int = 10,
) -> str:
    """
    R: Format conversation history + current query into a single prompt input.

    Features:
      - Sliding window: keeps only the last `max_messages` from history.
      - Spanish labeling: maps 'user' -> 'Usuario', etc.
      - Deterministic: consistent output format.
    """
    query = (current_query or "").strip()
    if not query:
        raise ValueError("current_query is required")

    history_list = list(history)

    # R: Apply sliding window to history
    if max_messages > 0:
        history_list = history_list[-max_messages:]

    if not history_list:
        return query

    # R: Build formatted string
    lines: list[str] = ["Historial de conversación:"]
    for message in history_list:
        label = _role_label(getattr(message, "role", ""))
        content = (getattr(message, "content", "") or "").strip()
        if content:
            lines.append(f"{label}: {content}")

    lines.append(f"Pregunta actual: {query}")
    return "\n".join(lines)
