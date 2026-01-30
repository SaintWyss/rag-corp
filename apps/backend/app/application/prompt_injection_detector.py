"""
Name: Prompt Injection Detector (Policy / Security Utility)

Qué es
------
Detector best-effort de señales de prompt-injection sobre texto NO confiable (chunks).
Devuelve:
  - risk_score normalizado en [0, 1]
  - flags categóricos (labels)
  - patterns matcheados (slugs)

Arquitectura
------------
- Estilo: Clean Architecture / Hexagonal
- Capa: Application (policy/security)
- Rol: Aplicar política de seguridad a inputs no confiables antes de construir contexto.

Patrones
--------
- Policy Object (funcional): `detect()` implementa una política de clasificación.
- Rule Engine (data-driven): reglas en `_PATTERNS` (regex + weight + flags).
- Fail-fast en configuración: modo inválido → error explícito (evita silently-wrong).

SOLID
-----
- SRP: solo detecta y filtra/ordena chunks; no hace retrieval ni formatting.
- OCP: agregar una regla = sumar un _PatternRule; no se cambia la lógica.
- DIP: opera sobre entidades del dominio (Chunk) y metadata plana; sin SDKs externos.

CRC (Component Card)
--------------------
Component: prompt_injection_detector
Responsibilities:
  - Detectar señales de prompt injection en texto no confiable
  - Proveer score normalizado y flags estables
  - Filtrar o downrankear chunks sin almacenar texto crudo
Collaborators:
  - domain.entities.Chunk (entrada)
Constraints:
  - No guardar texto crudo (solo labels/pattern slugs)
  - Determinismo: misma entrada → mismo resultado
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Literal, Mapping, Sequence, Tuple

from ..crosscutting.logger import logger
from ..domain.entities import Chunk

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

Mode = Literal["off", "exclude", "downrank"]


@dataclass(frozen=True, slots=True)
class DetectionResult:
    """
    R: Resultado inmutable del detector.

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
        R: Serializa el resultado para guardarlo en `chunk.metadata`.

        Importante:
          - No incluye texto crudo.
        """
        return {
            "risk_score": self.risk_score,
            "security_flags": list(self.flags),
            "security_patterns": list(self.patterns),
        }


@dataclass(frozen=True, slots=True)
class _PatternRule:
    """R: Regla data-driven (slug + regex + flags + peso)."""

    slug: str
    regex: re.Pattern[str]
    flags: Tuple[str, ...]
    weight: float


# ---------------------------------------------------------------------------
# Scoring policy
# ---------------------------------------------------------------------------

# R: Total_weight / THRESHOLD se normaliza a [0,1]. Mantener estable en el tiempo.
_RISK_SCORE_NORMALIZATION_THRESHOLD = 3.0

# R: Reglas ordenadas → matching determinista.
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


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------


def detect(text: str) -> DetectionResult:
    """
    R: Detecta señales de prompt injection en texto no confiable.

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

    # R: Matching determinista: recorremos reglas en orden fijo.
    for rule in _PATTERNS:
        if rule.regex.search(text):
            patterns.append(rule.slug)
            total_weight += rule.weight
            for flag in rule.flags:
                if flag not in flags:
                    flags.append(flag)

    if total_weight <= 0.0:
        return DetectionResult(risk_score=0.0, flags=(), patterns=())

    # R: Normalización a [0,1] con cap.
    risk_score = min(1.0, total_weight / _RISK_SCORE_NORMALIZATION_THRESHOLD)

    return DetectionResult(
        risk_score=float(risk_score),
        flags=tuple(flags),
        patterns=tuple(patterns),
    )


def is_flagged(metadata: Mapping | None, threshold: float) -> bool:
    """
    R: Determina si un chunk debe considerarse riesgoso según metadata ya calculada.

    Regla:
      - flagged si hay flags o si risk_score >= threshold
    """
    if not metadata:
        return False

    try:
        risk_score = float(metadata.get("risk_score", 0.0))
    except (TypeError, ValueError):
        risk_score = 0.0

    flags = metadata.get("security_flags") or []
    return bool(flags) or risk_score >= float(threshold)


def apply_injection_filter(
    chunks: Iterable[Chunk],
    mode: Mode,
    threshold: float,
) -> List[Chunk]:
    """
    R: Aplica modo de filtrado a una lista de chunks.

    Modes:
      - off: retorna chunks sin cambios
      - exclude: elimina chunks flaggeados
      - downrank: mueve chunks flaggeados al final (manteniendo similitud dentro de cada grupo)

    Nota:
      - No ejecuta `detect()`; usa `chunk.metadata`.
        (Esto permite detectar en ingestion o en retrieval stage y reusar resultado.)
    """
    mode_value = (mode or "off").strip().lower()
    chunk_list = list(chunks)

    if mode_value == "off":
        return chunk_list

    if mode_value not in ("exclude", "downrank"):
        # R: Fail-fast: config inválida debe explotar, no fallar silenciosamente.
        raise ValueError(f"Invalid injection filter mode: {mode_value}")

    flagged_count = sum(
        1 for c in chunk_list if is_flagged(getattr(c, "metadata", None), threshold)
    )
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
        return [
            c
            for c in chunk_list
            if not is_flagged(getattr(c, "metadata", None), threshold)
        ]

    # mode_value == "downrank"
    return sorted(
        chunk_list,
        key=lambda c: (
            is_flagged(getattr(c, "metadata", None), threshold),  # False primero
            -(
                getattr(c, "similarity", None) or 0.0
            ),  # mayor similitud primero dentro del grupo
        ),
    )
