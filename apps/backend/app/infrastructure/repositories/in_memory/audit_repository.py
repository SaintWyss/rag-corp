# =============================================================================
# FILE: infrastructure/repositories/in_memory/audit_repository.py
# =============================================================================
"""
In-Memory Answer Audit Repository for testing and development.

NOT FOR PRODUCTION USE - data is lost on restart.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID


class InMemoryAnswerAuditRepository:
    """
    In-memory implementation of AnswerAuditRepository.

    Useful for:
      - Unit testing
      - Local development without database
      - Integration tests
    """

    def __init__(self) -> None:
        self._records: Dict[str, dict] = {}  # record_id -> record data

    def save_audit_record(
        self,
        *,
        record_id: str,
        timestamp: str,
        user_id: UUID,
        workspace_id: UUID,
        query: str,
        answer_preview: str,
        confidence_level: str,
        confidence_value: float,
        requires_verification: bool,
        sources_count: int,
        source_documents: Optional[List[str]] = None,
        user_email: Optional[str] = None,
        suggested_department: Optional[str] = None,
        conversation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Persist an audit record."""
        is_high_risk = confidence_level == "low" or sources_count < 2

        self._records[record_id] = {
            "record_id": record_id,
            "timestamp": timestamp,
            "user_id": str(user_id),
            "workspace_id": str(workspace_id),
            "query": query,
            "answer_preview": answer_preview,
            "confidence_level": confidence_level,
            "confidence_value": confidence_value,
            "requires_verification": requires_verification,
            "sources_count": sources_count,
            "source_documents": source_documents or [],
            "user_email": user_email,
            "suggested_department": suggested_department,
            "conversation_id": conversation_id,
            "session_id": session_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "response_time_ms": response_time_ms,
            "was_rated": False,
            "rating": None,
            "is_high_risk": is_high_risk,
            "metadata": metadata or {},
        }

    def get_audit_record(self, record_id: str) -> Optional[dict]:
        """Fetch a specific audit record."""
        return self._records.get(record_id)

    def list_audit_records(
        self,
        *,
        workspace_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        confidence_level: Optional[str] = None,
        requires_verification: Optional[bool] = None,
        start_at: Optional[datetime] = None,
        end_at: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[dict]:
        """List audit records with filters."""
        results = list(self._records.values())

        # Apply filters
        if workspace_id is not None:
            results = [r for r in results if r["workspace_id"] == str(workspace_id)]
        if user_id is not None:
            results = [r for r in results if r["user_id"] == str(user_id)]
        if confidence_level is not None:
            results = [r for r in results if r["confidence_level"] == confidence_level]
        if requires_verification is not None:
            results = [
                r
                for r in results
                if r["requires_verification"] == requires_verification
            ]

        # Sort by timestamp descending
        results.sort(key=lambda x: x["timestamp"], reverse=True)

        # Apply pagination
        return results[offset : offset + limit]

    def list_high_risk_records(
        self,
        *,
        workspace_id: Optional[UUID] = None,
        start_at: Optional[datetime] = None,
        end_at: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[dict]:
        """List high-risk audit records for review."""
        results = [r for r in self._records.values() if r["is_high_risk"]]

        if workspace_id is not None:
            results = [r for r in results if r["workspace_id"] == str(workspace_id)]

        results.sort(key=lambda x: x["timestamp"], reverse=True)
        return results[:limit]

    def update_rating(
        self,
        record_id: str,
        *,
        was_rated: bool,
        rating: Optional[str] = None,
    ) -> bool:
        """Update the user rating for an audit record."""
        if record_id not in self._records:
            return False

        self._records[record_id]["was_rated"] = was_rated
        self._records[record_id]["rating"] = rating
        return True

    # -------------------------------------------------------------------------
    # Testing helpers
    # -------------------------------------------------------------------------
    def clear(self) -> None:
        """Clear all data (for testing)."""
        self._records.clear()

    def get_all_records(self) -> List[dict]:
        """Get all records (for testing)."""
        return list(self._records.values())

    def count_by_confidence(self) -> dict:
        """Count records by confidence level (for testing/analytics)."""
        high = sum(1 for r in self._records.values() if r["confidence_level"] == "high")
        medium = sum(
            1 for r in self._records.values() if r["confidence_level"] == "medium"
        )
        low = sum(1 for r in self._records.values() if r["confidence_level"] == "low")
        return {"high": high, "medium": medium, "low": low, "total": len(self._records)}
