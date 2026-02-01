"""
Name: Answer Query With History Use Case Unit Tests

Responsibilities:
  - Validate orchestration with conversation history
  - Ensure query rewriting is used for retrieval
  - Preserve original query in result metadata

Collaborators:
  - app.application.usecases.chat.answer_query_with_history
  - app.application.query_rewriter
"""

import pytest
from uuid import uuid4

from app.application.query_rewriter import RewriteResult
from app.application.usecases.chat.answer_query_with_history import (
    AnswerQueryWithHistoryInput,
    AnswerQueryWithHistoryUseCase,
)
from app.application.usecases.documents.document_results import AnswerQueryResult
from app.domain.entities import ConversationMessage, QueryResult
from app.domain.workspace_policy import WorkspaceActor
from app.identity.users import UserRole


class _ConversationRepo:
    def __init__(self, history):
        self._history = history

    def conversation_exists(self, conversation_id):
        return True

    def get_messages(self, conversation_id, limit):
        return self._history[:limit]

    def append_message(self, conversation_id, message):
        return None


class _AnswerQuerySpy:
    def __init__(self):
        self.last_input = None

    def execute(self, input_data):
        self.last_input = input_data
        return AnswerQueryResult(
            result=QueryResult(
                answer="ok",
                chunks=[],
                query=input_data.query,
                metadata={},
            )
        )


class _RewriterStub:
    def __init__(self, rewritten_query):
        self._rewritten_query = rewritten_query

    def rewrite(self, query, history):
        return RewriteResult(
            original_query=query,
            rewritten_query=self._rewritten_query,
            was_rewritten=True,
            reason="test",
        )


@pytest.mark.unit
def test_rewrite_is_used_for_retrieval_and_metadata_preserves_original():
    conversation_id = "conv-1"
    original_query = "¿y eso cuánto cuesta?"
    rewritten_query = "¿Cuánto cuesta el plan premium mencionado antes?"

    history = [
        ConversationMessage(role="user", content="Hablemos de planes premium"),
        ConversationMessage(role="assistant", content="El plan premium incluye soporte"),
    ]
    conversation_repo = _ConversationRepo(history)
    answer_query_spy = _AnswerQuerySpy()
    rewriter = _RewriterStub(rewritten_query)

    use_case = AnswerQueryWithHistoryUseCase(
        conversation_repository=conversation_repo,
        answer_query_use_case=answer_query_spy,
        query_rewriter=rewriter,
    )

    result = use_case.execute(
        AnswerQueryWithHistoryInput(
            conversation_id=conversation_id,
            query=original_query,
            workspace_id=uuid4(),
            actor=WorkspaceActor(user_id=uuid4(), role=UserRole.ADMIN),
            top_k=3,
        )
    )

    assert result.error is None
    assert answer_query_spy.last_input is not None
    assert answer_query_spy.last_input.query == rewritten_query
    assert result.result.query == original_query
    assert result.result.metadata["original_query"] == original_query
    assert result.result.metadata["rewritten_query"] == rewritten_query
    assert result.result.metadata["rewrite_applied"] is True
