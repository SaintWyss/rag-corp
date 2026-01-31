# =============================================================================
# FILE: application/usecases/chat/chat_utils.py
# =============================================================================
"""
===============================================================================
MODULE: Chat Utilities (Formatting & Helpers)
===============================================================================

Name:
    Chat Utilities

Responsibility:
    - Formatear historial de conversación para inyectar en el prompt del LLM.
    - Helpers de manipulación de mensajes.
    - Windowing strategy para limitar tokens de historial.

Why:
    - El LLM necesita contexto de la conversación previa para mantener coherencia.
    - Separamos esta lógica de los casos de uso para mantenerlos limpios (SRP).
    - Permite reutilizar el formateo en diferentes flujos (sync, streaming, etc).

Arquitectura:
    - Capa: Application (utility)
    - Estilo: Funciones puras (sin side effects)
    - Dependencias: solo domain.entities.ConversationMessage

-------------------------------------------------------------------------------
CRC (Module Card)
-------------------------------------------------------------------------------
Component: chat_utils
Responsibilities:
  - Formatear historial de conversación en texto estructurado
  - Aplicar sliding window para limitar mensajes
  - Mapear roles internos a etiquetas legibles
Collaborators:
  - domain.entities.ConversationMessage
Constraints:
  - Determinismo: misma entrada => misma salida
  - No modifica mensajes originales
===============================================================================
"""

from __future__ import annotations

from typing import Final, Iterable, List

from ....domain.entities import ConversationMessage

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
_DEFAULT_MAX_MESSAGES: Final[int] = 10
_HISTORY_HEADER: Final[str] = "Historial de conversación (contexto previo):"
_SEPARATOR: Final[str] = "-" * 40


def _role_label(role: str) -> str:
    """
    Mapea roles internos a etiquetas legibles para el LLM (en español).

    Mapping:
      - user -> Usuario
      - assistant/model -> Asistente
      - system/developer -> Sistema
    """
    role_norm = (role or "").strip().lower()
    if role_norm == "user":
        return "Usuario"
    if role_norm in {"assistant", "model"}:
        return "Asistente"
    if role_norm in {"system", "developer"}:
        return "Sistema"
    return role or "Desconocido"


def format_conversation_for_prompt(
    history: Iterable[ConversationMessage],
    current_query: str,
    *,
    max_messages: int = _DEFAULT_MAX_MESSAGES,
    include_current_query: bool = True,
) -> str:
    """
    Formatea el historial de conversación en un string único para el prompt.

    Formato generado:
        Historial de conversación (contexto previo):
        Usuario: Hola
        Asistente: Hola, ¿en qué puedo ayudarte?
        ----------------------------------------
        Pregunta actual: ¿Cuánto cuesta el producto?

    Args:
        history: iterable de mensajes previos (orden cronológico).
        current_query: la pregunta actual del usuario.
        max_messages: ventana deslizante (últimos N mensajes) para no saturar contexto.
        include_current_query: si True, agrega la línea "Pregunta actual: ...".

    Returns:
        String formateado listo para inyectar en el prompt del LLM.

    Nota:
        - Si no hay historial, solo devuelve el query actual (sin header).
        - Los mensajes vacíos se ignoran.
    """
    query = (current_query or "").strip()
    history_list = list(history)

    # Sliding window: últimos N mensajes
    if max_messages > 0:
        history_list = history_list[-max_messages:]

    lines: List[str] = []

    if history_list:
        lines.append(_HISTORY_HEADER)
        for message in history_list:
            label = _role_label(getattr(message, "role", ""))
            content = (getattr(message, "content", "") or "").strip()
            # Evitar mensajes vacíos
            if content:
                lines.append(f"{label}: {content}")
        lines.append(_SEPARATOR)

    if include_current_query and query:
        lines.append(f"Pregunta actual: {query}")

    # Si no hay nada formateado, al menos devolver el query
    if not lines and query:
        return query

    return "\n".join(lines)


def truncate_history(
    history: Iterable[ConversationMessage],
    max_messages: int = _DEFAULT_MAX_MESSAGES,
) -> List[ConversationMessage]:
    """
    Aplica sliding window al historial (últimos N mensajes).

    Útil cuando se necesita la lista de mensajes (no el string formateado).
    """
    history_list = list(history)
    if max_messages > 0:
        return history_list[-max_messages:]
    return history_list
