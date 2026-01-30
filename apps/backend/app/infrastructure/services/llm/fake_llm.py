"""
Name: Fake LLM Service (Deterministic Test Double)

Qué es
------
Implementación determinista de `domain.services.LLMService` para tests/CI.
No realiza IO, no llama APIs externas y permite probar:
  - generación sync (generate_answer)
  - streaming (generate_stream)
  - integración con chunks/context builder (de forma simplificada)

Arquitectura
------------
- Estilo: Clean Architecture / Hexagonal
- Capa: Infrastructure (test adapter / test double)
- Rol: reemplazar providers reales en tests sin red ni credenciales

Patrones
--------
- Test Double (Fake): simula LLM con salida determinista
- Adapter (conceptual): cumple contrato de LLMService sin SDKs externos

SOLID
-----
- SRP: produce respuestas deterministas (no decide retrieval ni reglas de negocio).
- OCP: se puede cambiar estrategia de determinismo sin tocar consumidores.
- LSP: puede sustituir a GoogleLLMService u otro provider si respeta el contrato.
- ISP/DIP: se mantiene en el contrato del dominio (LLMService, Chunk).

CRC (Class-Responsibility-Collaboration)
----------------------------------------
Class: FakeLLMService
Responsibilities:
  - Generar respuestas deterministas para query+context
  - Emitir stream incremental de respuesta (para probar UX/SSE)
  - Exponer identificadores estables (model_id, prompt_version)
Collaborators:
  - domain.entities.Chunk
  - domain.services.LLMService
Constraints:
  - Sin IO / sin dependencias externas
  - Determinismo total: mismas entradas → misma salida
"""

from __future__ import annotations

import hashlib
from typing import AsyncGenerator, List, Sequence

from ....crosscutting.exceptions import LLMError
from ....crosscutting.logger import logger
from ....domain.entities import Chunk
from ....domain.services import LLMService

# R: Tamaño de “trozo” para simular streaming (pequeño pero no demasiado ruidoso)
_STREAM_CHUNK_SIZE = 16


def _normalize(text: str) -> str:
    """R: Normalización mínima para estabilidad en tests."""
    return (text or "").strip()


def _build_context_from_chunks(chunks: Sequence[Chunk]) -> str:
    """
    R: Construye un contexto simple concatenando contenido de chunks.

    Nota:
      - No replica scoring/ranking; sólo sirve para integrar flujo RAG en tests.
    """
    parts = []
    for chunk in chunks:
        content = _normalize(getattr(chunk, "content", ""))
        if content:
            parts.append(content)
    return "\n".join(parts)


def _build_answer(query: str, context: str) -> str:
    """
    R: Produce una respuesta determinista derivada de (query, context).

    Estrategia:
      - hash = sha256("query|context") y usamos un prefijo como “firma”
      - mantiene salida estable para asserts (snapshot tests)
    """
    q = _normalize(query)
    c = _normalize(context)
    digest = hashlib.sha256(f"{q}|{c}".encode("utf-8")).hexdigest()[:16]
    return f"Respuesta simulada ({digest}) para: {q}"


class FakeLLMService(LLMService):
    """
    R: Deterministic LLMService for tests/CI.

    Utilidad:
      - Tests de endpoints
      - Tests de streaming/SSE
      - Tests de lógica de aplicación sin dependencia externa
    """

    MODEL_ID = "fake-llm-v1"
    PROMPT_VERSION = "fake"

    def __init__(self, *, stream_chunk_size: int = _STREAM_CHUNK_SIZE) -> None:
        """
        R: Inicializa el fake.

        Args:
            stream_chunk_size: tamaño del chunk para streaming (default 16)
        """
        if stream_chunk_size <= 0:
            raise ValueError("stream_chunk_size must be > 0")
        self._stream_chunk_size = stream_chunk_size

        # R: Evitar ruido en CI/tests: debug en vez de info.
        logger.debug(
            "FakeLLMService initialized",
            extra={
                "model_id": self.MODEL_ID,
                "prompt_version": self.PROMPT_VERSION,
                "stream_chunk_size": self._stream_chunk_size,
            },
        )

    def generate_answer(self, query: str, context: str) -> str:
        """
        R: Genera una respuesta determinista.

        Validación:
          - query no puede ser vacía (alineado a providers reales)
        """
        if not _normalize(query):
            raise LLMError("Query must not be empty")
        return _build_answer(query, context)

    async def generate_stream(
        self, query: str, chunks: List[Chunk]
    ) -> AsyncGenerator[str, None]:
        """
        R: Emite respuesta determinista en modo streaming.

        Garantías:
          - Orden estable
          - Chunks consecutivos de tamaño fijo (último puede ser menor)
        """
        if not _normalize(query):
            raise LLMError("Query must not be empty")

        context = _build_context_from_chunks(chunks)
        answer = _build_answer(query, context)

        for start in range(0, len(answer), self._stream_chunk_size):
            yield answer[start : start + self._stream_chunk_size]

    @property
    def prompt_version(self) -> str:
        """R: Versión estable del prompt (útil para logs/test asserts)."""
        return self.PROMPT_VERSION

    @property
    def model_id(self) -> str:
        """R: Identificador estable del modelo fake (útil para logs)."""
        return self.MODEL_ID
