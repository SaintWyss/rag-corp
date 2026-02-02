# =============================================================================
# FILE: infrastructure/repositories/in_memory/feedback_repository.py
# =============================================================================
"""
In-Memory Feedback Repository for testing and development.

NOT FOR PRODUCTION USE - data is lost on restart.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID


class InMemoryFeedbackRepository:
    """
    In-memory implementation of FeedbackRepository.

    Useful for:
      - Unit testing
      - Local development without database
      - Integration tests
    """

    def __init__(self) -> None:
        self._votes: Dict[str, dict] = {}  # vote_id -> vote data
        self._by_message: Dict[
            str, Dict[str, str]
        ] = {}  # "conv:msg" -> {user_id: vote_id}

    def _make_message_key(self, conversation_id: str, message_index: int) -> str:
        return f"{conversation_id}:{message_index}"

    def save_vote(
        self,
        *,
        conversation_id: str,
        message_index: int,
        user_id: UUID,
        vote: str,
        comment: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_at: Optional[datetime] = None,
    ) -> str:
        """Persist a vote and return the vote ID."""
        vote_id = f"vote-{uuid.uuid4().hex[:12]}"
        msg_key = self._make_message_key(conversation_id, message_index)
        user_key = str(user_id)

        # Check for duplicates
        if msg_key in self._by_message and user_key in self._by_message[msg_key]:
            existing_id = self._by_message[msg_key][user_key]
            return existing_id  # Return existing vote (idempotent)

        vote_data = {
            "vote_id": vote_id,
            "conversation_id": conversation_id,
            "message_index": message_index,
            "user_id": str(user_id),
            "vote": vote,
            "comment": comment,
            "tags": tags or [],
            "created_at": (created_at or datetime.now(timezone.utc)).isoformat(),
        }

        self._votes[vote_id] = vote_data

        if msg_key not in self._by_message:
            self._by_message[msg_key] = {}
        self._by_message[msg_key][user_key] = vote_id

        return vote_id

    def get_vote(
        self, *, conversation_id: str, message_index: int, user_id: UUID
    ) -> Optional[dict]:
        """Get existing vote for a user on a specific message."""
        msg_key = self._make_message_key(conversation_id, message_index)
        user_key = str(user_id)

        if msg_key not in self._by_message:
            return None
        if user_key not in self._by_message[msg_key]:
            return None

        vote_id = self._by_message[msg_key][user_key]
        return self._votes.get(vote_id)

    def list_votes_for_conversation(self, conversation_id: str) -> List[dict]:
        """List all votes for a conversation."""
        return [
            v for v in self._votes.values() if v["conversation_id"] == conversation_id
        ]

    def count_votes(
        self,
        *,
        workspace_id: Optional[UUID] = None,
        vote_type: Optional[str] = None,
        start_at: Optional[datetime] = None,
        end_at: Optional[datetime] = None,
    ) -> dict:
        """Count votes by type for analytics."""
        # Simplified implementation - ignores workspace_id and dates
        up = sum(1 for v in self._votes.values() if v["vote"] == "up")
        down = sum(1 for v in self._votes.values() if v["vote"] == "down")
        neutral = sum(1 for v in self._votes.values() if v["vote"] == "neutral")
        return {"up": up, "down": down, "neutral": neutral, "total": len(self._votes)}

    # -------------------------------------------------------------------------
    # Testing helpers
    # -------------------------------------------------------------------------
    def clear(self) -> None:
        """Clear all data (for testing)."""
        self._votes.clear()
        self._by_message.clear()

    def get_all_votes(self) -> List[dict]:
        """Get all votes (for testing)."""
        return list(self._votes.values())
