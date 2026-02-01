# apps/backend/app/crosscutting/streaming.py
"""
===============================================================================
MÓDULO: Streaming SSE (Server-Sent Events) para respuestas del LLM
===============================================================================

Objetivo
--------
- Emitir tokens en tiempo real
- Enviar sources primero
- Enviar evento done al final
- Manejar desconexión del cliente sin romper el worker/API

-------------------------------------------------------------------------------
CRC (Component Card)
-------------------------------------------------------------------------------
Componente:
  stream_answer()

Responsabilidades:
  - Formatear eventos SSE
  - Orquestar stream desde LLMService.generate_stream

Colaboradores:
  - domain.services.LLMService
  - domain.repositories.ConversationRepository
===============================================================================
"""

from __future__ import annotations

import json
from typing import AsyncGenerator, List, Optional

from fastapi import Request
from fastapi.responses import StreamingResponse

from ..domain.entities import Chunk, ConversationMessage
from ..domain.repositories import ConversationRepository
from ..domain.services import LLMService
from .logger import logger


async def stream_answer(
    query: str,
    chunks: List[Chunk],
    llm_service: LLMService,
    request: Request,
    conversation_id: Optional[str] = None,
    conversation_repository: Optional[ConversationRepository] = None,
) -> StreamingResponse:
    """
    SSE Events:
      - sources: {"sources":[...], "conversation_id": "..."}
      - token: {"token":"..."}
      - done: {"answer":"...", "conversation_id":"..."}
      - error: {"error":"..."}
    """
    return StreamingResponse(
        _generate_sse(
            query,
            chunks,
            llm_service,
            request,
            conversation_id,
            conversation_repository,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _generate_sse(
    query: str,
    chunks: List[Chunk],
    llm_service: LLMService,
    request: Request,
    conversation_id: Optional[str],
    conversation_repository: Optional[ConversationRepository],
) -> AsyncGenerator[str, None]:
    full_answer = ""

    try:
        sources = [
            {"chunk_id": str(c.chunk_id), "content": c.content[:200]} for c in chunks
        ]
        yield _sse_event(
            "sources", {"sources": sources, "conversation_id": conversation_id}
        )

        async for token in llm_service.generate_stream(query, chunks):
            if await request.is_disconnected():
                logger.info("SSE: cliente desconectado")
                return

            full_answer += token
            yield _sse_event("token", {"token": token})

        if conversation_id and conversation_repository:
            conversation_repository.append_message(
                conversation_id,
                ConversationMessage(role="assistant", content=full_answer),
            )

        yield _sse_event(
            "done", {"answer": full_answer, "conversation_id": conversation_id}
        )

    except Exception as e:
        logger.error("SSE stream error", extra={"error": str(e)})
        yield _sse_event("error", {"error": "Error durante streaming"})


def _sse_event(event: str, data: dict) -> str:
    # SSE: cada evento termina con doble newline
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
