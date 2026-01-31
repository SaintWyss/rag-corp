"""
============================================================
TARJETA CRC — infrastructure/repositories/in_memory_conversation_repo.py
============================================================
Class: InMemoryConversationRepository

Responsibilities:
  - Mantener conversaciones en memoria (por conversation_id).
  - Almacenar mensajes en orden de llegada (append-only).
  - Enforzar un máximo de historial por conversación (max_messages) usando deque(maxlen).
  - Permitir:
      - crear conversación (id nuevo)
      - consultar existencia
      - append de mensajes
      - obtener mensajes (con limit opcional)

Collaborators:
  - domain.entities.ConversationMessage (entidad del dominio)
  - domain.repositories.ConversationRepository (contrato)
  - collections.deque (buffer acotado, eficiente para append)
  - threading.Lock (thread-safety)

Constraints / Notes (Clean / SOLID):
  - Thread-safe: todas las operaciones sobre el dict/deques ocurren bajo lock.
  - Repo puro: no aplica reglas de negocio; sólo almacena/retorna datos.
  - Política de retención:
      - max_messages limita automáticamente (se descartan los más viejos).
  - get_messages:
      - limit=None => devuelve todo
      - limit<=0 => devuelve todo (contrato explícito para evitar sorpresas)
============================================================
"""

from __future__ import annotations

from collections import deque
from threading import Lock
from typing import Deque, Dict, List
from uuid import uuid4

from ....domain.entities import ConversationMessage
from ....domain.repositories import ConversationRepository


class InMemoryConversationRepository(ConversationRepository):
    """
    Repositorio in-memory, thread-safe, para historial de conversaciones.

    Modelo mental:
    - _conversations actúa como tabla:
        conversation_id (str UUID) -> deque[ConversationMessage]
    - deque(maxlen=N) garantiza “cap” automático:
        al superar N, descarta por la izquierda (los más viejos).
    """

    def __init__(self, max_messages: int = 12):
        # Guard rails: evita configuraciones inválidas que rompan el contrato.
        if max_messages <= 0:
            raise ValueError("max_messages must be > 0")

        self._max_messages = max_messages
        self._lock = Lock()
        self._conversations: Dict[str, Deque[ConversationMessage]] = {}

    # =========================================================
    # Helpers internos
    # =========================================================
    def _ensure_conversation(self, conversation_id: str) -> Deque[ConversationMessage]:
        """
        Obtiene el deque de una conversación, creándolo si no existe.

        Por qué:
        - centraliza la semántica “upsert” que hoy está duplicada en append_message.
        - mantiene el maxlen consistente.
        """
        dq = self._conversations.get(conversation_id)
        if dq is None:
            dq = deque(maxlen=self._max_messages)
            self._conversations[conversation_id] = dq
        return dq

    # =========================================================
    # API del repositorio
    # =========================================================
    def create_conversation(self) -> str:
        """
        Crea una conversación nueva y devuelve su ID.

        Decisión:
        - ID es str(uuid4()) para evitar depender de UUID en interfaces externas.
        - Inicializa el deque con maxlen para aplicar cap desde el primer mensaje.
        """
        conversation_id = str(uuid4())
        with self._lock:
            # Creamos explícitamente para que conversation_exists sea true inmediatamente.
            self._conversations[conversation_id] = deque(maxlen=self._max_messages)
        return conversation_id

    def conversation_exists(self, conversation_id: str) -> bool:
        """
        Indica si la conversación existe en el repo.

        Nota:
        - Es un check de existencia, no de “tiene mensajes”.
        """
        with self._lock:
            return conversation_id in self._conversations

    def append_message(
        self, conversation_id: str, message: ConversationMessage
    ) -> None:
        """
        Agrega un mensaje al final del historial.

        Semántica:
        - Si la conversación no existe, se crea (upsert).
        - deque(maxlen) asegura que el historial no crezca indefinidamente.
        """
        with self._lock:
            dq = self._ensure_conversation(conversation_id)
            dq.append(message)

    def get_messages(
        self, conversation_id: str, limit: int | None = None
    ) -> List[ConversationMessage]:
        """
        Devuelve los mensajes de una conversación.

        Contrato:
        - Si no existe, devuelve [].
        - limit=None => todo el historial (hasta max_messages).
        - limit<=0 => todo el historial (evita “sorpresas”).
        - limit>0 => últimos `limit` mensajes (tail).

        Nota performance:
        - Convertimos a list fuera del lock para minimizar tiempo de bloqueo.
        """
        with self._lock:
            messages = list(self._conversations.get(conversation_id, []))

        if limit is None or limit <= 0:
            return messages

        # Tail slice: últimos N (si N > len, Python devuelve todo).
        return messages[-limit:]
