"""
Name: Prompt Injection Detector

Responsibilities:
  - Detect prompt injection signals in untrusted text
  - Provide stable risk scoring and categorical flags
  - Avoid storing raw text (labels only)
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, List

from ..domain.entities import Chunk


@dataclass(frozen=True)
class DetectionResult:
    risk_score: float
    flags: List[str]
    patterns: List[str]


@dataclass(frozen=True)
class _PatternRule:
    slug: str
    regex: re.Pattern
    flags: List[str]
    weight: float


_RISK_SCORE_THRESHOLD = 3.0

_PATTERNS: List[_PatternRule] = [
    _PatternRule(
        slug="ignore_instructions",
        regex=re.compile(r"\b(ignore|ignora)\b.+\b(instructions|instrucciones)\b", re.I),
        flags=["instruction_override"],
        weight=1.2,
    ),
    _PatternRule(
        slug="system_prompt",
        regex=re.compile(r"\b(system prompt|prompt del sistema)\b", re.I),
        flags=["exfiltration_attempt"],
        weight=1.2,
    ),
    _PatternRule(
        slug="developer_message",
        regex=re.compile(r"\b(developer message|mensaje del desarrollador)\b", re.I),
        flags=["policy_override"],
        weight=1.0,
    ),
    _PatternRule(
        slug="reveal_secrets",
        regex=re.compile(
            r"\b(reveal|leak|exfiltrate|revela|filtra|confidencial)\b", re.I
        ),
        flags=["exfiltration_attempt"],
        weight=1.0,
    ),
    _PatternRule(
        slug="tool_abuse",
        regex=re.compile(r"\b(tools?|herramientas|function calling)\b", re.I),
        flags=["tool_abuse"],
        weight=0.7,
    ),
    _PatternRule(
        slug="policy_override",
        regex=re.compile(
            r"\b(policy|pol[ií]tica|bypass|jailbreak|override|anula|sin restricciones)\b",
            re.I,
        ),
        flags=["policy_override"],
        weight=1.0,
    ),
    _PatternRule(
        slug="act_as",
        regex=re.compile(r"\b(act as|act[úu]a como)\b", re.I),
        flags=["instruction_override"],
        weight=0.8,
    ),
    _PatternRule(
        slug="prompt_reference",
        regex=re.compile(r"\bprompt\b", re.I),
        flags=[],
        weight=0.3,
    ),
]


def detect(text: str) -> DetectionResult:
    """
    Detect prompt injection signals in text.

    Returns:
        DetectionResult with risk_score in [0,1], flags, and matched pattern slugs.
    """
    if not text or not text.strip():
        return DetectionResult(risk_score=0.0, flags=[], patterns=[])

    total_weight = 0.0
    flags: List[str] = []
    patterns: List[str] = []

    for rule in _PATTERNS:
        if rule.regex.search(text):
            patterns.append(rule.slug)
            total_weight += rule.weight
            for flag in rule.flags:
                if flag not in flags:
                    flags.append(flag)

    if total_weight <= 0:
        return DetectionResult(risk_score=0.0, flags=[], patterns=[])

    risk_score = min(1.0, total_weight / _RISK_SCORE_THRESHOLD)
    return DetectionResult(risk_score=risk_score, flags=flags, patterns=patterns)


def is_flagged(metadata: dict | None, threshold: float) -> bool:
    """Return True if metadata indicates a risky chunk."""
    if not metadata:
        return False
    try:
        risk_score = float(metadata.get("risk_score", 0.0))
    except (TypeError, ValueError):
        risk_score = 0.0
    flags = metadata.get("security_flags") or []
    return bool(flags) or risk_score >= threshold


def apply_injection_filter(
    chunks: Iterable[Chunk],
    mode: str,
    threshold: float,
) -> List[Chunk]:
    """
    Apply injection filter mode to a list of chunks.

    Modes:
      - off: return chunks unchanged
      - exclude: drop flagged chunks
      - downrank: move flagged chunks to the end
    """
    mode_value = (mode or "off").strip().lower()
    chunk_list = list(chunks)

    if mode_value == "off":
        return chunk_list

    if mode_value == "exclude":
        return [chunk for chunk in chunk_list if not is_flagged(chunk.metadata, threshold)]

    if mode_value == "downrank":
        return sorted(
            chunk_list,
            key=lambda c: (
                is_flagged(c.metadata, threshold),
                -(c.similarity or 0.0),
            ),
        )

    return chunk_list
