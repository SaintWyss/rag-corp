"""
Name: Google Gemini LLM Service Implementation (Adapter)

Qué hace
--------
Implementación concreta de `domain.services.LLMService` usando Google GenAI (Gemini).
Este componente se encarga de:
  - Formatear prompts versionados (PromptLoader)
  - Generar respuestas RAG basadas en contexto (context-only policy)
  - Reintentar errores transitorios con exponential backoff + jitter (tenacity)
  - Streaming incremental para UX (SSE / token-like chunks)

Arquitectura
------------
- Estilo: Clean Architecture / Hexagonal
- Capa: Infrastructure
- Rol: Adapter hacia un proveedor externo (Google GenAI)

Patrones
--------
- Adapter: traduce contrato `LLMService` a llamadas al SDK (genai)
- Policy (fail-fast / retry): `retry.py` define qué errores reintentar
- Factory/DI (fuera de este módulo): el composition root inyecta API key, loader, builder, etc.

SOLID
-----
- SRP: este service sólo orquesta prompt + llamada al proveedor + manejo de errores.
- OCP: swappeable por otro provider (OpenAI/Claude) sin cambiar use cases.
- LSP: respeta el contrato de `LLMService`.
- ISP/DIP: depende de abstracciones (LLMService, PromptLoader, ContextBuilderPort), no de detalles del SDK.

CRC (Class-Responsibility-Collaboration)
----------------------------------------
Class: GoogleLLMService
Responsibilities:
  - Generar respuesta completa (generate_answer) basada en prompt versionado
  - Emitir stream incremental (generate_stream) para mejor UX
  - Aplicar política "context-only" (no llamar LLM si no hay contexto)
  - Reintentar errores transitorios (retry) y loguear observabilidad básica
Collaborators:
  - PromptLoader (infra.prompts): arma template versionado
  - ContextBuilderPort (port por duck-typing): convierte chunks → context string
  - google.genai.Client: SDK externo
  - retry.create_retry_decorator: resiliencia
Constraints:
  - Streaming: si el error ocurre a mitad de stream, NO se reintenta (no se puede reemitir tokens ya enviados)
  - Respuestas en español (por prompt/policy)
"""

from __future__ import annotations

import os
from typing import AsyncGenerator, List, Optional, Protocol

from google import genai

from ....crosscutting.exceptions import LLMError
from ....crosscutting.logger import logger
from ....domain.entities import Chunk
from ....domain.services import LLMService
from ...prompts import PromptLoader, get_prompt_loader
from ..retry import create_retry_decorator


class ContextBuilderPort(Protocol):
    """
    R: Port (duck-typed) para construir contexto desde chunks.

    Nota de arquitectura:
      - Esto evita que Infrastructure dependa de Application.
      - El composition root puede inyectar `application.context_builder.ContextBuilder`.
    """

    def build(self, chunks: List[Chunk]) -> tuple[str, int]: ...


class GoogleLLMService(LLMService):
    """
    R: Google Gemini implementation of LLMService.

    Implementa el contrato del dominio usando Gemini (por defecto gemini-1.5-flash).
    """

    DEFAULT_MODEL_ID = "gemini-1.5-flash"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        client: genai.Client | None = None,
        model_id: str | None = None,
        prompt_loader: Optional[PromptLoader] = None,
        context_builder: ContextBuilderPort | None = None,
        retry_decorator=None,
    ) -> None:
        """
        R: Inicializa el servicio (preferible vía DI).

        Args:
            api_key: API key (ideal: inyectar desde Settings)
            client: Cliente genai preconstruido (útil para tests)
            model_id: Override del modelo (default: gemini-1.5-flash)
            prompt_loader: Loader versionado (default: singleton)
            context_builder: Builder para chunks → string (inyectable)
            retry_decorator: Decorator tenacity (inyectable para tests)

        Raises:
            LLMError: si no hay API key y no se inyectó `client`.
        """
        resolved_key = (api_key or os.getenv("GOOGLE_API_KEY") or "").strip()
        if not resolved_key and client is None:
            logger.error("GoogleLLMService: GOOGLE_API_KEY not configured")
            raise LLMError("GOOGLE_API_KEY not configured")

        # R: SDK client (inyectable para tests; si no, se crea con api_key)
        self._client = client or genai.Client(api_key=resolved_key)

        # R: Config del modelo
        self._model_id = (model_id or self.DEFAULT_MODEL_ID).strip()

        # R: Prompt loader versionado (inyectable)
        self._prompt_loader = prompt_loader or get_prompt_loader()

        # R: Context builder (inyectable). Si no se inyecta, se construye lazy como fallback.
        #     Ideal: mover ContextBuilder a un puerto de dominio/crosscutting y siempre inyectar.
        self._context_builder = context_builder

        # R: Preconstruimos wrappers con retry para no redefinir closures por llamada.
        decorator = retry_decorator or create_retry_decorator()
        self._generate_content = decorator(self._client.models.generate_content)
        self._create_stream = decorator(self._client.models.generate_content_stream)

        logger.info(
            "GoogleLLMService initialized",
            extra={
                "model_id": self._model_id,
                "prompt_version": self._prompt_loader.version,
            },
        )

    @property
    def prompt_version(self) -> str:
        """R: Versión actual del prompt (para observabilidad)."""
        return self._prompt_loader.version

    @property
    def model_id(self) -> str:
        """R: Identificador del modelo (para logs/debug)."""
        return self._model_id

    def _context_only_fallback(self) -> str:
        """
        R: Respuesta estándar si no hay contexto.

        Evita alucinaciones: si no hay fuentes, no llamamos al LLM.
        """
        return (
            "No encontré información suficiente en tus documentos para responder con certeza. "
            "Probá reformular la pregunta o cargá documentos relevantes."
        )

    def _build_prompt(self, *, query: str, context: str) -> str:
        """R: Arma el prompt final usando template versionado."""
        return self._prompt_loader.format(context=context, query=query)

    def _get_context_builder(self) -> ContextBuilderPort:
        """
        R: Obtiene el context builder.

        Nota:
          - Este fallback mantiene compatibilidad sin acoplar el módulo en import-time.
          - Recomendación: inyectarlo desde el composition root.
        """
        if self._context_builder is not None:
            return self._context_builder

        # R: Import lazy para evitar dependencia directa de capa application al importar el módulo.
        from ....application.context_builder import get_context_builder  # noqa: PLC0415

        self._context_builder = get_context_builder()
        return self._context_builder

    def generate_answer(self, query: str, context: str) -> str:
        """
        R: Genera una respuesta basada en `query` + `context` (RAG).

        Política:
          - Si `context` está vacío → no llamamos al LLM (context-only).
        """
        if not (query or "").strip():
            raise LLMError("Query must not be empty")

        if not (context or "").strip():
            return self._context_only_fallback()

        prompt = self._build_prompt(query=query, context=context)

        try:
            # R: Llamada al provider con retry (errores transitorios)
            response = self._generate_content(model=self._model_id, contents=prompt)
            text = (getattr(response, "text", "") or "").strip()

            logger.info(
                "GoogleLLMService: Response generated",
                extra={
                    "model_id": self._model_id,
                    "prompt_version": self.prompt_version,
                    "answer_chars": len(text),
                },
            )
            return text

        except LLMError:
            raise
        except Exception as exc:
            logger.error(
                "GoogleLLMService: Generation failed",
                exc_info=True,
                extra={
                    "model_id": self._model_id,
                    "prompt_version": self.prompt_version,
                    "error_type": type(exc).__name__,
                },
            )
            raise LLMError("Failed to generate response") from exc

    def generate_text(self, prompt: str, max_tokens: int = 200) -> str:
        """
        R: Genera texto plano a partir de un prompt (tareas auxiliares).

        Nota:
          - max_tokens es best-effort; algunos providers requieren config extra.
        """
        if not (prompt or "").strip():
            raise LLMError("Prompt must not be empty")

        try:
            response = self._generate_content(model=self._model_id, contents=prompt)
            text = (getattr(response, "text", "") or "").strip()

            logger.info(
                "GoogleLLMService: Text generated",
                extra={
                    "model_id": self._model_id,
                    "prompt_version": self.prompt_version,
                    "max_tokens": max_tokens,
                    "text_chars": len(text),
                },
            )
            return text

        except LLMError:
            raise
        except Exception as exc:
            logger.error(
                "GoogleLLMService: Text generation failed",
                exc_info=True,
                extra={
                    "model_id": self._model_id,
                    "prompt_version": self.prompt_version,
                    "error_type": type(exc).__name__,
                },
            )
            raise LLMError("Failed to generate text") from exc

    async def generate_stream(
        self, query: str, chunks: List[Chunk]
    ) -> AsyncGenerator[str, None]:
        """
        R: Stream incremental de la respuesta (SSE friendly).

        Importante:
          - Si el error ocurre durante la iteración del stream, NO reintentamos,
            porque no podemos garantizar idempotencia del output (ya se emitieron tokens).
          - Reintentamos solamente la creación del stream (errores al iniciar).
        """
        if not (query or "").strip():
            raise LLMError("Query must not be empty")

        # R: Construimos context en este método por contrato del dominio (recibe chunks).
        #     El builder se inyecta para respetar DIP y evitar depender de Application.
        context_builder = self._get_context_builder()
        context, chunks_used = context_builder.build(chunks)

        if not context.strip():
            # R: Si no hay fuentes, devolvemos fallback en modo streaming.
            yield self._context_only_fallback()
            return

        prompt = self._build_prompt(query=query, context=context)

        try:
            # R: Creamos stream con retry (errores transitorios al iniciar)
            stream_iter = self._create_stream(model=self._model_id, contents=prompt)

            # R: Emitimos texto a medida que llega (chunk.text).
            for piece in stream_iter:
                text = getattr(piece, "text", None)
                if text:
                    yield text

            logger.info(
                "GoogleLLMService: Streaming completed",
                extra={
                    "model_id": self._model_id,
                    "prompt_version": self.prompt_version,
                    "chunks_used": chunks_used,
                },
            )

        except Exception as exc:
            logger.error(
                "GoogleLLMService: Streaming failed",
                exc_info=True,
                extra={
                    "model_id": self._model_id,
                    "prompt_version": self.prompt_version,
                    "chunks_used": chunks_used,
                    "error_type": type(exc).__name__,
                },
            )
            raise LLMError("Failed to stream response") from exc
