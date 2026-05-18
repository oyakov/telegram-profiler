"""Unit tests for LeadService — run_saved_search limit and UUID validation."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.services.lead_service import LeadService
from src.db.models.marketing import LeadSearch
from src.db.models.content import Contact


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session():
    s = AsyncMock()
    s.add = MagicMock()
    return s


def _scalar_result(obj):
    r = MagicMock()
    r.scalar_one_or_none.return_value = obj
    return r


def _scalars_all_result(items):
    r = MagicMock()
    r.scalars.return_value.all.return_value = items
    return r


# ---------------------------------------------------------------------------
# run_saved_search — uses page_size from filter, not hardcoded 50
# ---------------------------------------------------------------------------

class TestRunSavedSearch:
    @pytest.mark.asyncio
    async def test_uses_page_size_from_profile_filter(self):
        """run_saved_search must pass the filter's page_size as the limit, not 50."""
        search = LeadSearch(
            id=uuid4(),
            name="Big search",
            profile_filter={"company": "Acme", "page_size": 150},
        )
        contact = Contact(
            id=uuid4(), first_name="Alice", source="test",
            is_lead=True, lead_score=5.0, is_tracked=False, is_personal=False,
            our_channel_ratio=0.0, total_messages_synced=0,
            interests=[], skills=[], lead_context={},
        )

        session = _make_session()
        session.execute = AsyncMock(return_value=_scalar_result(search))

        # Patch the repo method to capture what limit was passed
        captured = {}

        async def fake_get_matching(profile_filter, limit=200, offset=0):
            captured["limit"] = limit
            return [contact] * min(limit, 1)  # return 1 contact

        with patch.object(LeadService, "__init__", lambda self, s: (
            setattr(self, "session", s) or
            setattr(self, "repo", MagicMock(
                get_matching_contacts=AsyncMock(side_effect=fake_get_matching),
                count_matching_contacts=AsyncMock(return_value=1),
            )) or
            setattr(self, "contact_svc", MagicMock(map_to_response=lambda c: {"id": str(c.id)}))
        )):
            svc = LeadService(session)
            result = await svc.run_saved_search(str(search.id))

        assert captured.get("limit") == 150, (
            f"Expected limit=150 (from page_size), got {captured.get('limit')}"
        )

    @pytest.mark.asyncio
    async def test_defaults_to_200_when_no_page_size_in_filter(self):
        """When profile_filter has no page_size, default limit must be 200 (not 50)."""
        search = LeadSearch(
            id=uuid4(),
            name="Default search",
            profile_filter={"company": "Acme"},  # no page_size key
        )
        contact = Contact(
            id=uuid4(), first_name="Bob", source="test",
            is_lead=True, lead_score=3.0, is_tracked=False, is_personal=False,
            our_channel_ratio=0.0, total_messages_synced=0,
            interests=[], skills=[], lead_context={},
        )

        session = _make_session()
        session.execute = AsyncMock(return_value=_scalar_result(search))

        captured = {}

        async def fake_get_matching(profile_filter, limit=200, offset=0):
            captured["limit"] = limit
            return [contact]

        with patch.object(LeadService, "__init__", lambda self, s: (
            setattr(self, "session", s) or
            setattr(self, "repo", MagicMock(
                get_matching_contacts=AsyncMock(side_effect=fake_get_matching),
            )) or
            setattr(self, "contact_svc", MagicMock(map_to_response=lambda c: {"id": str(c.id)}))
        )):
            svc = LeadService(session)
            result = await svc.run_saved_search(str(search.id))

        assert captured.get("limit") == 200, (
            f"Expected default limit=200, got {captured.get('limit')}"
        )
        assert captured["limit"] != 50, "Hardcoded limit=50 regression detected"

    @pytest.mark.asyncio
    async def test_invalid_uuid_raises_value_error(self):
        """Non-UUID search_id must raise ValueError → 404, not a DB DataError → 500."""
        svc = LeadService(_make_session())
        with pytest.raises(ValueError, match="Search not found"):
            await svc.run_saved_search("not-a-uuid")

    @pytest.mark.asyncio
    async def test_missing_search_raises_value_error(self):
        session = _make_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))
        svc = LeadService(session)
        with pytest.raises(ValueError, match="Search not found"):
            await svc.run_saved_search(str(uuid4()))


# ---------------------------------------------------------------------------
# get_lead_history — UUID validation (already in service, verify stays)
# ---------------------------------------------------------------------------

class TestGetLeadHistory:
    @pytest.mark.asyncio
    async def test_invalid_uuid_raises_value_error(self):
        svc = LeadService(_make_session())
        with pytest.raises(ValueError, match="Contact not found"):
            await svc.get_lead_history("bad-uuid")
