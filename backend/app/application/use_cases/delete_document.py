"""
Name: Delete Document Use Case

Responsibilities:
  - Soft delete a document by ID

Collaborators:
  - domain.repositories.DocumentRepository
"""

from uuid import UUID

from ...domain.repositories import DocumentRepository


class DeleteDocumentUseCase:
    """R: Soft delete a document."""

    def __init__(self, repository: DocumentRepository):
        self.repository = repository

    def execute(self, document_id: UUID) -> bool:
        return self.repository.soft_delete_document(document_id)
