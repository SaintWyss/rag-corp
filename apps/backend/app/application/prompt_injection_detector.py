# =============================================================================
# FILE: application/prompt_injection_detector.py
# =============================================================================
"""
===============================================================================
POLICY: Prompt Injection Detector (Security Utility)
===============================================================================

Name:
    Prompt Injection Detector (Policy / Security Utility)

Qué es:
    Detector best-effort de señales de prompt-injection sobre texto NO confiable
    (por ejemplo, chunks recuperados de documentos).

Devuelve:
    - risk_score normalizado en [0, 1]
    - flags categóricos (labels estables)
    - patterns matcheados (slugs de reglas)

Arquitectura:
    - Estilo: Clean Architecture / Hexagonal
    - Capa: Application (policy/security)
    - Rol: Aplicar política de seguridad a inputs no confiables antes del contexto/LLM.

Patrones:
    - Policy Object: detect() implementa una política de clasificación.
    - Rule Engine data-driven: reglas definidas en _PATTERNS.
    - Fail-fast: config inválida => error explícito (evita comportamiento silencioso).

SOLID:
    - SRP: solo detecta y filtra/reordena; no hace retrieval ni formatting.
    - OCP: agregar regla = sumar _PatternRule; la lógica no cambia.
    - DIP: opera sobre entidades del dominio (Chunk) y metadata simple; sin SDKs externos.

CRC (Component Card):
    Component: prompt_injection_detector
    Responsibilities:
      - Detectar señales de prompt injection en texto no confiable
      - Proveer score normalizado y flags estables
      - Filtrar o reordenar chunks según policy, sin modificar el texto
    Collaborators:
      - domain.entities.Chunk (entrada)
    Constraints:
      - No guardar texto crudo (solo labels/pattern slugs en metadata)
      - Determinismo: misma entrada => mismo resultado
===============================================================================
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Iterable, List, Literal, Mapping, Tuple

from ..crosscutting.logger import logger
from ..domain.entities import Chunk

# -----------------------------------------------------------------------------
# Public types
# -----------------------------------------------------------------------------
Mode = Literal["off", "exclude", "downrank"]

# -----------------------------------------------------------------------------
# Metadata contract (keys consistentes en todo el sistema)
# -----------------------------------------------------------------------------
METADATA_KEY_RISK_SCORE: Final[str] = "risk_score"
METADATA_KEY_SECURITY_FLAGS: Final[str] = "security_flags"
METADATA_KEY_DETECTED_PATTERNS: Final[str] = "detected_patterns"


@dataclass(frozen=True, slots=True)
class DetectionResult:
    """
    Resultado inmutable del detector.

    risk_score:
        - normalizado en [0, 1]
        - 0 = no señales, 1 = señales fuertes

    flags/patterns:
        - tuples inmutables para evitar mutaciones accidentales
    """

    risk_score: float
    flags: Tuple[str, ...]
    patterns: Tuple[str, ...]

    def to_metadata(self) -> dict:
        """
        Serializa el resultado para guardarlo en `chunk.metadata`.

        Importante:
            - No incluye texto crudo.
            - Mantiene las keys alineadas con ingestion / procesamiento async.
        """
        return {
            METADATA_KEY_RISK_SCORE: float(self.risk_score),
            METADATA_KEY_SECURITY_FLAGS: list(self.flags),
            METADATA_KEY_DETECTED_PATTERNS: list(self.patterns),
        }


@dataclass(frozen=True, slots=True)
class _PatternRule:
    """Regla data-driven (slug + regex + flags + peso)."""

    slug: str
    regex: re.Pattern[str]
    flags: Tuple[str, ...]
    weight: float


# -----------------------------------------------------------------------------
# Scoring policy
# -----------------------------------------------------------------------------
# Normalización: total_weight / THRESHOLD -> [0,1] (cap).
_RISK_SCORE_NORMALIZATION_THRESHOLD: Final[float] = 3.0

# Reglas ordenadas => matching determinista.
_PATTERNS: Tuple[_PatternRule, ...] = (
    _PatternRule(
        slug="ignore_instructions",
        regex=re.compile(
            r"\b(ignore|ignora)\b.+\b(instructions|instrucciones)\b", re.I
        ),
        flags=("instruction_override",),
        weight=1.2,
    ),
    _PatternRule(
        slug="system_prompt",
        regex=re.compile(r"\b(system prompt|prompt del sistema)\b", re.I),
        flags=("exfiltration_attempt",),
        weight=1.2,
    ),
    _PatternRule(
        slug="developer_message",
        regex=re.compile(r"\b(developer message|mensaje del desarrollador)\b", re.I),
        flags=("policy_override",),
        weight=1.0,
    ),
    _PatternRule(
        slug="reveal_secrets",
        regex=re.compile(
            r"\b(reveal|leak|exfiltrate|revela|filtra|confidencial)\b", re.I
        ),
        flags=("exfiltration_attempt",),
        weight=1.0,
    ),
    _PatternRule(
        slug="tool_abuse",
        regex=re.compile(r"\b(tools?|herramientas|function calling)\b", re.I),
        flags=("tool_abuse",),
        weight=0.7,
    ),
    _PatternRule(
        slug="policy_override",
        regex=re.compile(
            r"\b(policy|pol[ií]tica|bypass|jailbreak|override|anula|sin restricciones)\b",
            re.I,
        ),
        flags=("policy_override",),
        weight=1.0,
    ),
    _PatternRule(
        slug="act_as",
        regex=re.compile(r"\b(act as|act[úu]a como)\b", re.I),
        flags=("instruction_override",),
        weight=0.8,
    ),
    _PatternRule(
        slug="prompt_reference",
        regex=re.compile(r"\bprompt\b", re.I),
        flags=(),
        weight=0.3,
    ),
)


# -----------------------------------------------------------------------------
# Core API
# -----------------------------------------------------------------------------
def detect(text: str) -> DetectionResult:
    """
    Detecta señales de prompt injection en texto no confiable.

    Returns:
        DetectionResult:
          - risk_score ∈ [0, 1]
          - flags: labels categóricos (sin texto crudo)
          - patterns: slugs de reglas matcheadas
    """
    if not text or not text.strip():
        return DetectionResult(risk_score=0.0, flags=(), patterns=())

    total_weight = 0.0
    flags: List[str] = []
    patterns: List[str] = []

    # Matching determinista: reglas en orden fijo.
    for rule in _PATTERNS:
        if rule.regex.search(text):
            patterns.append(rule.slug)
            total_weight += rule.weight
            for flag in rule.flags:
                if flag not in flags:
                    flags.append(flag)

    if total_weight <= 0.0:
        return DetectionResult(risk_score=0.0, flags=(), patterns=())

    risk_score = min(1.0, total_weight / _RISK_SCORE_NORMALIZATION_THRESHOLD)
    return DetectionResult(
        risk_score=float(risk_score),
        flags=tuple(flags),
        patterns=tuple(patterns),
    )


def is_flagged(metadata: Mapping | None, threshold: float) -> bool:
    """
    Determina si un chunk debe considerarse riesgoso según metadata ya calculada.

    Regla:
      - flagged si hay flags o si risk_score >= threshold
    """
    if not metadata:
        return False

    try:
        risk_score = float(metadata.get(METADATA_KEY_RISK_SCORE, 0.0))
    except (TypeError, ValueError):
        risk_score = 0.0

    flags = metadata.get(METADATA_KEY_SECURITY_FLAGS) or []
    return bool(flags) or risk_score >= float(threshold)


def apply_injection_filter(
    chunks: Iterable[Chunk],
    mode: Mode,
    threshold: float,
) -> List[Chunk]:
    """
    Aplica política de filtrado/reordenamiento a chunks.

    Modes:
      - off: retorna chunks sin cambios
      - exclude: elimina chunks flaggeados
      - downrank: mueve chunks flaggeados al final (estable, preserva orden original)

    Nota:
      - No ejecuta detect(); usa chunk.metadata (precalculada en ingest/procesamiento).
        Si metadata no existe, se considera "no flaggeado".
    """
    mode_value = (mode or "off").strip().lower()
    chunk_list = list(chunks)

    if mode_value == "off":
        return chunk_list

    if mode_value not in ("exclude", "downrank"):
        raise ValueError(f"Invalid injection filter mode: {mode_value}")

    # Precalcular flagged para evitar recomputar y asegurar consistencia.
    flagged_mask = [
        is_flagged(getattr(c, "metadata", None), threshold) for c in chunk_list
    ]
    flagged_count = sum(1 for v in flagged_mask if v)

    logger.debug(
        "Applying injection filter",
        extra={
            "mode": mode_value,
            "threshold": float(threshold),
            "flagged_count": flagged_count,
            "total": len(chunk_list),
        },
    )

    if mode_value == "exclude":
        return [c for c, flagged in zip(chunk_list, flagged_mask) if not flagged]

    # mode_value == "downrank" => partición estable (no re-sortea por similarity)
    safe = [c for c, flagged in zip(chunk_list, flagged_mask) if not flagged]
    risky = [c for c, flagged in zip(chunk_list, flagged_mask) if flagged]
    return safe + risky
