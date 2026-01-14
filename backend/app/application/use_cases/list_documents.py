"""
Name: List Documents Use Case

Responsibilities:
  - Retrieve document metadata for listing
  - Apply pagination defaults

Collaborators:
  - domain.repositories.DocumentRepository
"""

from typing import List

from ...domain.entities import Document
from ...domain.repositories import DocumentRepository


class ListDocumentsUseCase:
    """R: List document metadata."""

    def __init__(self, repository: DocumentRepository):
        self.repository = repository

    def execute(self, limit: int = 50, offset: int = 0) -> List[Document]:
        return self.repository.list_documents(limit=limit, offset=offset)
