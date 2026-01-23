"""
Name: Prompt Loader

Responsibilities:
  - Load prompt templates from files
  - Support versioning via PROMPT_VERSION env var
  - Cache loaded templates for performance

Collaborators:
  - config: Get prompt_version setting
  - prompts/*.md: Template files

Notes:
  - Templates use {context} and {query} placeholders
  - Falls back to v1 if version not found
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from ...platform.logger import logger


# R: Directory containing prompt templates
PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


class PromptLoader:
    """
    R: Load and cache prompt templates by version.
    """

    def __init__(self, version: str = "v1"):
        """
        R: Initialize loader with version.

        Args:
            version: Prompt version (e.g., "v1", "v2")
        """
        self.version = version
        self._template: Optional[str] = None

    def get_template(self) -> str:
        """
        R: Get prompt template, loading from file if needed.

        Returns:
            Prompt template string with {context} and {query} placeholders

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        if self._template is None:
            self._template = self._load_template()
        return self._template

    def _load_template(self) -> str:
        """
        R: Load template from file.
        """
        filename = f"{self.version}_answer_es.md"
        filepath = PROMPTS_DIR / filename

        if not filepath.exists():
            logger.error(
                f"Prompt template not found: {filepath}",
                extra={"version": self.version},
            )
            raise FileNotFoundError(f"Prompt template not found: {filepath}")

        template = filepath.read_text(encoding="utf-8")
        logger.info(
            "Loaded prompt template",
            extra={"version": self.version, "chars": len(template)},
        )
        return template

    def format(self, context: str, query: str) -> str:
        """
        R: Format template with context and query.

        Args:
            context: Assembled context from chunks
            query: User's question

        Returns:
            Formatted prompt ready for LLM
        """
        template = self.get_template()
        return template.format(context=context, query=query)


@lru_cache
def get_prompt_loader() -> PromptLoader:
    """
    R: Get singleton PromptLoader with configured version.
    """
    from ...platform.config import get_settings

    settings = get_settings()
    return PromptLoader(version=settings.prompt_version)
