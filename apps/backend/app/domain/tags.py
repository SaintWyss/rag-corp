"""
Name: Tag Normalization

Responsibilities:
  - Normalize tag inputs from metadata payloads
  - Provide consistent tag list semantics for documents
"""

from typing import Any


def normalize_tags(metadata: dict[str, Any] | None) -> list[str]:
    if not metadata:
        return []

    raw = metadata.get("tags")
    if raw is None:
        return []

    if isinstance(raw, str):
        candidates = [raw]
    elif isinstance(raw, list):
        candidates = raw
    else:
        return []

    tags: list[str] = []
    for item in candidates:
        if not isinstance(item, str):
            continue
        cleaned = item.strip()
        if cleaned and cleaned not in tags:
            tags.append(cleaned)
    return tags
