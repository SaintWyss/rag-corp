"""
Name: Google Gemini LLM Service Implementation

Responsibilities:
  - Implement LLMService interface for Google Gemini 1.5 Flash
  - Generate RAG answers using versioned prompt templates
  - Apply business rules (context-only responses)
  - Handle generation errors gracefully
  - Retry transient errors with exponential backoff + jitter
  - Stream responses token-by-token for better UX

Collaborators:
  - domain.services.LLMService: Interface implementation
  - infrastructure.prompts.PromptLoader: Template loading
  - google.genai: Google Gen AI SDK
  - retry: Resilience helper for transient errors

Constraints:
  - Prompt loaded from versioned template files
  - No control over generation parameters
  - Responses in Spanish (by prompt)
  - Retries on 429, 5xx, timeouts

Notes:
  - Implements Service interface from domain layer
  - Can be swapped with other providers (OpenAI, Claude)
  - Uses dependency inversion principle
"""

import os
from typing import Optional, List, AsyncGenerator

from google import genai

from ....domain.entities import Chunk
from ....crosscutting.logger import logger
from ....crosscutting.exceptions import LLMError
from ...prompts import PromptLoader, get_prompt_loader
from ..retry import create_retry_decorator
from ....application.context_builder import get_context_builder


class GoogleLLMService:
    """
    R: Google Gemini implementation of LLMService.

    Implements domain.services.LLMService interface
    using Gemini 1.5 Flash model.
    """

    def __init__(
        self, api_key: str | None = None, prompt_loader: Optional[PromptLoader] = None
    ):
        """
        R: Initialize Google LLM Service.

        Args:
            api_key: Google API key (defaults to GOOGLE_API_KEY env var)
            prompt_loader: Optional PromptLoader (defaults to singleton)

        Raises:
            LLMError: If API key not configured
        """
        # R: Use provided key or fall back to environment variable
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")

        if not self.api_key:
            logger.error("GoogleLLMService: GOOGLE_API_KEY not configured")
            raise LLMError("GOOGLE_API_KEY not configured")

        # R: Initialize Google Gen AI client
        self.client = genai.Client(api_key=self.api_key)
        self.model_id = "gemini-1.5-flash"

        # R: Get prompt loader (use provided or default singleton)
        self.prompt_loader = prompt_loader or get_prompt_loader()

        logger.info(
            "GoogleLLMService initialized",
            extra={"prompt_version": self.prompt_loader.version},
        )

    @property
    def prompt_version(self) -> str:
        """R: Get current prompt version."""
        return self.prompt_loader.version

    def generate_answer(self, query: str, context: str) -> str:
        """
        R: Generate answer based on query and retrieved context.

        Implements LLMService.generate_answer()

        Raises:
            LLMError: If response generation fails
        """
        # R: Format prompt using versioned template
        prompt = self.prompt_loader.format(context=context, query=query)

        try:
            # R: Create retry decorator for API calls
            retry_decorator = create_retry_decorator()

            @retry_decorator
            def _generate_with_retry(prompt_text: str) -> str:
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=prompt_text,
                )
                return (response.text or "").strip()

            result = _generate_with_retry(prompt)
            logger.info(
                "GoogleLLMService: Response generated",
                extra={"prompt_version": self.prompt_version},
            )
            return result
        except LLMError:
            raise
        except Exception as e:
            logger.error(f"GoogleLLMService: Generation failed: {e}")
            raise LLMError(f"Failed to generate response: {e}")

    async def generate_stream(
        self, query: str, chunks: List[Chunk]
    ) -> AsyncGenerator[str, None]:
        """
        R: Stream answer token by token.

        Implements LLMService.generate_stream()

        Args:
            query: User's question
            chunks: Retrieved context chunks

        Yields:
            Individual tokens as they are generated

        Raises:
            LLMError: If streaming fails
        """
        # R: Build context from chunks
        context_builder = get_context_builder()
        context, _ = context_builder.build(chunks)

        # R: Format prompt using versioned template
        prompt = self.prompt_loader.format(context=context, query=query)

        try:
            # R: Use streaming API
            for chunk in self.client.models.generate_content_stream(
                model=self.model_id,
                contents=prompt,
            ):
                if chunk.text:
                    yield chunk.text

            logger.info(
                "GoogleLLMService: Streaming response completed",
                extra={"prompt_version": self.prompt_version},
            )
        except Exception as e:
            logger.error(f"GoogleLLMService: Streaming failed: {e}")
            raise LLMError(f"Failed to stream response: {e}")
