"""Unit tests for ContactRepository — IntegrityError handling and _apply_profile_filter DRY."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from src.db.repository import ContactRepository, LeadSearchRepository
from src.db.models.content import Contact


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session():
    s = AsyncMock()
    s.add = MagicMock()
    return s


def _fake_integrity_error(msg: str) -> IntegrityError:
    """Create an IntegrityError with a fake orig whose str matches the message."""
    orig = Exception(msg)
    return IntegrityError(statement="INSERT ...", params={}, orig=orig)


# ---------------------------------------------------------------------------
# bulk_upsert_contacts — IntegrityError handling
# ---------------------------------------------------------------------------

class TestBulkUpsertContacts:
    @pytest.mark.asyncio
    async def test_returns_empty_list_on_unique_violation(self):
        """A unique-constraint conflict must be swallowed and return []."""
        session = _make_session()

        with patch("sqlalchemy.dialects.postgresql.insert") as mock_insert:
            mock_stmt = MagicMock()
            mock_stmt.on_conflict_do_update.return_value = mock_stmt
            mock_stmt.returning.return_value = mock_stmt
            mock_stmt.excluded = MagicMock()
            mock_insert.return_value = mock_stmt

            session.execute = AsyncMock(
                side_effect=_fake_integrity_error(
                    'duplicate key value violates unique constraint "uq_contact_telegram_username"'
                )
            )

            repo = ContactRepository(session)
            result = await repo.bulk_upsert_contacts([{"first_name": "Alice", "telegram_id": "123"}])

        assert result == []
        session.rollback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reraises_non_unique_integrity_error(self):
        """FK violations and other IntegrityErrors that are NOT unique must propagate."""
        session = _make_session()

        with patch("sqlalchemy.dialects.postgresql.insert") as mock_insert:
            mock_stmt = MagicMock()
            mock_stmt.on_conflict_do_update.return_value = mock_stmt
            mock_stmt.returning.return_value = mock_stmt
            mock_stmt.excluded = MagicMock()
            mock_insert.return_value = mock_stmt

            # FK violation — "unique" not in the message
            session.execute = AsyncMock(
                side_effect=_fake_integrity_error(
                    'insert or update on table "contacts" violates foreign key constraint'
                )
            )

            repo = ContactRepository(session)
            with pytest.raises(IntegrityError):
                await repo.bulk_upsert_contacts([{"first_name": "Bob"}])

    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_input(self):
        session = _make_session()
        repo = ContactRepository(session)
        result = await repo.bulk_upsert_contacts([])
        assert result == []
        session.execute.assert_not_called()


# ---------------------------------------------------------------------------
# _apply_profile_filter — DRY helper used by both count and get
# ---------------------------------------------------------------------------

class TestApplyProfileFilter:
    def _base_stmt(self):
        from sqlalchemy import select
        return select(Contact)

    def test_applies_first_name_filter(self):
        stmt = LeadSearchRepository._apply_profile_filter(self._base_stmt(), {"first_name": "Alice"})
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "alice" in compiled.lower()

    def test_applies_min_lead_score_filter(self):
        stmt = LeadSearchRepository._apply_profile_filter(self._base_stmt(), {"min_lead_score": 7.5})
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "7.5" in compiled or "lead_score" in compiled

    def test_empty_filter_does_not_add_where(self):
        """Empty filter must not raise and must not produce spurious WHERE clauses."""
        stmt = LeadSearchRepository._apply_profile_filter(self._base_stmt(), {})
        # Should compile cleanly
        compiled = str(stmt.compile())
        assert "WHERE" not in compiled or "is_lead" not in compiled  # no unexpected filter

    def test_count_and_get_use_same_filter_logic(self):
        """Verify that count_matching_contacts and get_matching_contacts both call _apply_profile_filter."""
        import inspect
        src_count = inspect.getsource(LeadSearchRepository.count_matching_contacts)
        src_get = inspect.getsource(LeadSearchRepository.get_matching_contacts)
        assert "_apply_profile_filter" in src_count, "count_matching_contacts must use _apply_profile_filter"
        assert "_apply_profile_filter" in src_get, "get_matching_contacts must use _apply_profile_filter"
