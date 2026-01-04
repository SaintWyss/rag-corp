"""
Name: Google Gemini LLM Service Implementation

Responsibilities:
  - Implement LLMService interface for Google Gemini 1.5 Flash
  - Generate RAG answers using versioned prompt templates
  - Apply business rules (context-only responses)
  - Handle generation errors gracefully
  - Retry transient errors with exponential backoff + jitter

Collaborators:
  - domain.services.LLMService: Interface implementation
  - infrastructure.prompts.PromptLoader: Template loading
  - google.generativeai: Google Gemini SDK
  - retry: Resilience helper for transient errors

Constraints:
  - Prompt loaded from versioned template files
  - No control over generation parameters
  - Responses in Spanish (by prompt)
  - No streaming support
  - Retries on 429, 5xx, timeouts

Notes:
  - Implements Service interface from domain layer
  - Can be swapped with other providers (OpenAI, Claude)
  - Uses dependency inversion principle
"""

import os
from typing import Optional

import google.generativeai as genai

from ...logger import logger
from ...exceptions import LLMError
from ..prompts import PromptLoader, get_prompt_loader
from .retry import create_retry_decorator


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

        # R: Configure Google API client
        genai.configure(api_key=self.api_key)

        # R: Initialize model
        self.model = genai.GenerativeModel("gemini-1.5-flash")

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
                response = self.model.generate_content(prompt_text)
                return response.text.strip()

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
