"""
Name: Prompt Loader (Versioned Templates with Frontmatter)

Responsibilities:
  - Load policy + versioned prompt templates from organized directories
  - Parse YAML frontmatter for metadata validation
  - Support safe versioning via settings (v1, v2, ...)
  - Cache loaded templates in-memory per instance
  - Format prompt safely (replace only declared inputs)
  - Fallback to v1 if configured version template is missing

Collaborators:
  - crosscutting.config.get_settings (prompt_version)
  - app/prompts/{capability}/*.md (organized templates)
  - logger (observability)

Patterns:
  - Repository-like (filesystem-backed templates)
  - Composition (policy + versioned template)
  - Frontmatter parsing for metadata
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

from ...crosscutting.logger import logger

PROMPTS_DIR = (Path(__file__).resolve().parents[2] / "prompts").resolve()

# Subdirectories
POLICY_DIR = "policy"
RAG_ANSWER_DIR = "rag_answer"

# Defaults
DEFAULT_POLICY_FILE = "secure_contract_es.md"
DEFAULT_LANG = "es"

_VERSION_RE = re.compile(r"^v\d+$")
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

TOKEN_CONTEXT = "{context}"
TOKEN_QUERY = "{query}"


@dataclass
class PromptMetadata:
    """R: Parsed frontmatter metadata from prompt file."""

    type: str = ""
    version: str = ""
    lang: str = ""
    description: str = ""
    author: str = ""
    updated: str = ""
    inputs: list[str] = field(default_factory=list)


def parse_frontmatter(content: str) -> tuple[PromptMetadata, str]:
    """
    R: Parse YAML frontmatter from markdown content.

    Returns:
        Tuple of (metadata, body_without_frontmatter)
    """
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return PromptMetadata(), content

    yaml_block = match.group(1)
    body = content[match.end() :]

    # Simple YAML parsing (no external dependency)
    metadata = PromptMetadata()
    current_key = ""
    inputs_list: list[str] = []

    for line in yaml_block.split("\n"):
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue

        # Handle list items (for inputs)
        if line.strip().startswith("- "):
            if current_key == "inputs":
                inputs_list.append(line.strip()[2:].strip())
            continue

        # Handle key: value pairs
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            # Handle multiline strings (>) - just take what's on same line or next
            if value == ">":
                value = ""
            elif value:
                current_key = key
                if key == "type":
                    metadata.type = value
                elif key == "version":
                    metadata.version = value
                elif key == "lang":
                    metadata.lang = value
                elif key == "description":
                    metadata.description = value
                elif key == "author":
                    metadata.author = value
                elif key == "updated":
                    metadata.updated = value
                elif key == "inputs":
                    current_key = "inputs"
            else:
                current_key = key
        elif current_key == "description" and line.strip():
            # Continuation of multiline description
            metadata.description += " " + line.strip()

    metadata.inputs = inputs_list
    return metadata, body


class PromptLoader:
    """
    R: Load and cache prompt templates by version with frontmatter support.

    CRC:
      Responsibilities:
        - Resolve safe prompt paths in organized directory structure
        - Load policy + version template with frontmatter parsing
        - Cache composed prompt
        - Format prompt replacing only declared input tokens
        - Validate inputs match frontmatter declaration
      Collaborators:
        - filesystem (Path.read_text)
        - config (prompt_version)
      Constraints:
        - No path traversal via version
        - Policy included once and before template
        - Tokens must exist and match declared inputs
    """

    def __init__(
        self,
        version: str = "v1",
        lang: str = DEFAULT_LANG,
        capability: str = RAG_ANSWER_DIR,
        *,
        prompts_dir: Path = PROMPTS_DIR,
    ):
        self.version = self._validate_version(version)
        self.lang = lang
        self.capability = capability
        self._prompts_dir = prompts_dir

        self._policy: Optional[str] = None
        self._policy_meta: Optional[PromptMetadata] = None
        self._template: Optional[str] = None
        self._template_meta: Optional[PromptMetadata] = None
        self._composed: Optional[str] = None

    @property
    def metadata(self) -> Optional[PromptMetadata]:
        """R: Return template metadata (after loading)."""
        return self._template_meta

    def get_template(self) -> str:
        """R: Return composed prompt (policy + version template) with caching."""
        if self._composed is None:
            self._composed = self._compose_template()
        return self._composed

    def format(self, context: str, query: str) -> str:
        """
        R: Safe formatting: only replace {context} and {query}.

        Validates that template declares these inputs in frontmatter.
        """
        template = self.get_template()
        self._validate_tokens_present(template)

        # Validate inputs match frontmatter if available
        if self._template_meta and self._template_meta.inputs:
            expected = set(self._template_meta.inputs)
            provided = {"context", "query"}
            if not expected.issubset(provided):
                missing = expected - provided
                logger.warning(
                    "Template expects inputs not provided",
                    extra={"missing": list(missing)},
                )

        return template.replace(TOKEN_CONTEXT, context).replace(TOKEN_QUERY, query)

    @staticmethod
    def _validate_version(version: str) -> str:
        v = (version or "").strip()
        if not _VERSION_RE.match(v):
            raise ValueError(
                f"Invalid prompt version '{version}'. Expected v1, v2, ..."
            )
        return v

    def _policy_path(self) -> Path:
        return self._prompts_dir / POLICY_DIR / DEFAULT_POLICY_FILE

    def _template_path(self, version: str) -> Path:
        return self._prompts_dir / self.capability / f"{version}_{self.lang}.md"

    def _load_policy(self) -> str:
        path = self._policy_path()
        if not path.exists():
            logger.error("Policy contract not found", extra={"path": str(path)})
            raise FileNotFoundError(f"Policy contract not found: {path}")

        content = path.read_text(encoding="utf-8")
        self._policy_meta, body = parse_frontmatter(content)

        logger.info(
            "Loaded policy contract",
            extra={
                "chars": len(body),
                "version": self._policy_meta.version,
            },
        )
        return body.strip()

    def _load_template_for_version(self, version: str) -> str:
        path = self._template_path(version)
        if not path.exists():
            raise FileNotFoundError(f"Prompt template not found: {path}")

        content = path.read_text(encoding="utf-8")
        self._template_meta, body = parse_frontmatter(content)

        logger.info(
            "Loaded prompt template",
            extra={
                "version": version,
                "chars": len(body),
                "declared_inputs": self._template_meta.inputs,
            },
        )
        return body

    def _load_template_with_fallback(self) -> str:
        try:
            return self._load_template_for_version(self.version)
        except FileNotFoundError:
            if self.version != "v1":
                logger.warning(
                    "Prompt template missing; falling back to v1",
                    extra={"requested_version": self.version},
                )
                return self._load_template_for_version("v1")
            raise

    def _compose_template(self) -> str:
        if self._policy is None:
            self._policy = self._load_policy()
        self._template = self._load_template_with_fallback()
        return f"{self._policy}\n\n{self._template}".strip()

    @staticmethod
    def _validate_tokens_present(template: str) -> None:
        missing = []
        if TOKEN_CONTEXT not in template:
            missing.append(TOKEN_CONTEXT)
        if TOKEN_QUERY not in template:
            missing.append(TOKEN_QUERY)
        if missing:
            raise ValueError(
                f"Prompt template missing required tokens: {', '.join(missing)}"
            )


@lru_cache
def get_prompt_loader() -> PromptLoader:
    """R: Singleton PromptLoader configured by settings.prompt_version."""
    from ...crosscutting.config import get_settings

    settings = get_settings()
    return PromptLoader(version=settings.prompt_version)
