"""
Prompt Infrastructure (Infrastructure Layer)

Qué es
------
Facade/Barrel del paquete `infrastructure.prompts`.
Expone una API pública estable para cargar y formatear prompts versionados.

Arquitectura
------------
- Clean Architecture / Hexagonal
- Capa: Infrastructure
- Rol: Proveer templates (archivos .md) a los adapters LLM (Google/OpenAI/etc.)

Patrones
--------
- Facade / Barrel: re-export de símbolos públicos del paquete.
- Frontmatter: metadata parsing para validación.
"""

from .loader import PromptLoader, PromptMetadata, get_prompt_loader, parse_frontmatter

__all__ = ["PromptLoader", "PromptMetadata", "get_prompt_loader", "parse_frontmatter"]
