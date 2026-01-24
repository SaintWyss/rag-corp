"""
Name: Streaming Response Handler

Responsibilities:
  - Server-Sent Events (SSE) streaming for LLM responses
  - Token-by-token delivery to frontend
  - Graceful error handling during stream

Collaborators:
  - domain.services.LLMService
  - routes (FastAPI endpoints)
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
    Stream LLM response as Server-Sent Events.

    SSE Format:
        event: token
        data: {"token": "word"}

        event: done
        data: {"answer": "full answer", "conversation_id": "..."}

        event: error
        data: {"error": "message"}
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
            "X-Accel-Buffering": "no",  # Disable nginx buffering
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
    """Generate SSE events from LLM stream."""
    full_answer = ""

    try:
        # Send sources first
        sources = [
            {"chunk_id": str(c.chunk_id), "content": c.content[:200]} for c in chunks
        ]
        yield _sse_event(
            "sources",
            {"sources": sources, "conversation_id": conversation_id},
        )

        # Stream tokens from LLM
        async for token in llm_service.generate_stream(query, chunks):
            # Check if client disconnected
            if await request.is_disconnected():
                logger.info("SSE: Client disconnected")
                return

            full_answer += token
            yield _sse_event("token", {"token": token})

        if conversation_id and conversation_repository:
            conversation_repository.append_message(
                conversation_id,
                ConversationMessage(role="assistant", content=full_answer),
            )

        # Send completion event
        yield _sse_event(
            "done", {"answer": full_answer, "conversation_id": conversation_id}
        )

    except Exception as e:
        logger.error(f"SSE stream error: {e}")
        yield _sse_event("error", {"error": str(e)})


def _sse_event(event: str, data: dict) -> str:
    """Format SSE event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
