"""
Name: List Documents Use Case

Responsibilities:
  - Retrieve document metadata for listing
  - Apply pagination defaults

Collaborators:
  - domain.repositories.DocumentRepository
"""

from dataclasses import dataclass
from typing import List

from ...domain.entities import Document
from ...domain.repositories import DocumentRepository
from ...pagination import decode_cursor, encode_cursor


@dataclass
class ListDocumentsOutput:
    documents: List[Document]
    next_cursor: str | None = None


class ListDocumentsUseCase:
    """R: List document metadata."""

    def __init__(self, repository: DocumentRepository):
        self.repository = repository

    def execute(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        cursor: str | None = None,
        query: str | None = None,
        status: str | None = None,
        tag: str | None = None,
        sort: str | None = None,
    ) -> ListDocumentsOutput:
        resolved_offset = decode_cursor(cursor) if cursor else offset
        documents = self.repository.list_documents(
            limit=limit + 1,
            offset=resolved_offset,
            query=query,
            status=status,
            tag=tag,
            sort=sort,
        )
        next_cursor = (
            encode_cursor(resolved_offset + limit) if len(documents) > limit else None
        )
        return ListDocumentsOutput(
            documents=documents[:limit],
            next_cursor=next_cursor,
        )
