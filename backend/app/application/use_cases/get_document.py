"""
Name: Get Document Use Case

Responsibilities:
  - Retrieve a single document by ID

Collaborators:
  - domain.repositories.DocumentRepository
"""

from uuid import UUID
from typing import Optional

from ...domain.entities import Document
from ...domain.repositories import DocumentRepository


class GetDocumentUseCase:
    """R: Fetch a document by ID."""

    def __init__(self, repository: DocumentRepository):
        self.repository = repository

    def execute(self, document_id: UUID) -> Optional[Document]:
        return self.repository.get_document(document_id)
