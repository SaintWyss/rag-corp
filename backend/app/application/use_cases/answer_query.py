"""
Name: Answer Query Use Case

Responsibilities:
  - Orchestrate complete RAG flow (retrieval + generation)
  - Coordinate repository, embedding service, and LLM service
  - Apply business logic (top_k, context assembly, error handling)
  - Return QueryResult with answer and sources

Collaborators:
  - domain.repositories.DocumentRepository: Chunk retrieval
  - domain.services.EmbeddingService: Query embedding generation
  - domain.services.LLMService: Answer generation
  - domain.entities.QueryResult: Response encapsulation

Constraints:
  - No HTTP concerns (that's the presentation layer's job)
  - No knowledge of PostgreSQL, Google API, etc. (abstracted by interfaces)
  - Business logic only (orchestration + rules)

Notes:
  - This is the "star" use case of the RAG system
  - Demonstrates Clean Architecture benefits:
    * Testable (mock repo/services)
    * Independent of frameworks
    * Swappable implementations (change providers without touching this)
  - Follows Single Responsibility Principle
"""

from dataclasses import dataclass
from typing import List

from ...domain.entities import QueryResult, Chunk
from ...domain.repositories import DocumentRepository
from ...domain.services import EmbeddingService, LLMService


@dataclass
class AnswerQueryInput:
    """
    R: Input data for AnswerQuery use case.
    
    Attributes:
        query: User's natural language question
        top_k: Number of similar chunks to retrieve (default: 5)
    """
    query: str
    top_k: int = 5


class AnswerQueryUseCase:
    """
    R: Use case for complete RAG flow (retrieval + generation).
    
    This is the main business logic for answering user questions
    using retrieved context from the document repository.
    """
    
    def __init__(
        self,
        repository: DocumentRepository,
        embedding_service: EmbeddingService,
        llm_service: LLMService
    ):
        """
        R: Initialize use case with injected dependencies.
        
        Args:
            repository: Document repository for chunk retrieval
            embedding_service: Service for generating embeddings
            llm_service: Service for generating answers
        """
        self.repository = repository
        self.embedding_service = embedding_service
        self.llm_service = llm_service
    
    def execute(self, input_data: AnswerQueryInput) -> QueryResult:
        """
        R: Execute RAG flow: embed query → retrieve chunks → generate answer.
        
        Args:
            input_data: Query and configuration (top_k)
        
        Returns:
            QueryResult with generated answer and source chunks
        
        Business Rules:
            1. If no chunks found, return "not found" message
            2. Context is assembled by concatenating chunk contents
            3. LLM must answer based only on provided context
        """
        if input_data.top_k <= 0:
            return QueryResult(
                answer="No encontré documentos relacionados a tu pregunta.",
                chunks=[],
                query=input_data.query,
                metadata={"top_k": input_data.top_k, "chunks_found": 0}
            )
        # R: STEP 1 - Generate query embedding
        query_embedding = self.embedding_service.embed_query(input_data.query)
        
        # R: STEP 2 - Retrieve similar chunks from repository
        chunks = self.repository.find_similar_chunks(
            embedding=query_embedding,
            top_k=input_data.top_k
        )
        
        # R: STEP 3 - Assemble context from retrieved chunks
        if not chunks:
            # R: Business rule: If no relevant chunks, return fallback message
            return QueryResult(
                answer="No encontré documentos relacionados a tu pregunta.",
                chunks=[],
                query=input_data.query,
                metadata={"top_k": input_data.top_k, "chunks_found": 0}
            )
        
        # R: Concatenate chunk contents to form context
        context = "\n\n".join([chunk.content for chunk in chunks])
        
        # R: STEP 4 - Generate answer using LLM
        answer = self.llm_service.generate_answer(
            query=input_data.query,
            context=context
        )
        
        # R: Return structured result with answer and sources
        return QueryResult(
            answer=answer,
            chunks=chunks,
            query=input_data.query,
            metadata={
                "top_k": input_data.top_k,
                "chunks_found": len(chunks)
            }
        )
