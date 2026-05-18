"""Unit tests for ContactService — UUID validation, field whitelist, and response mapping."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

from src.services.contact_service import ContactService, _ALLOWED_UPDATE_FIELDS
from src.db.models.content import Contact


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session():
    """Return a mock async session."""
    session = AsyncMock()
    session.add = MagicMock()
    return session


def _make_contact(**kwargs) -> Contact:
    defaults = dict(
        id=uuid4(),
        first_name="Alice",
        last_name="Smith",
        email="alice@example.com",
        source="test",
        is_lead=False,
        is_tracked=False,
        is_personal=False,
        lead_score=0.0,
        our_channel_ratio=0.0,
        total_messages_synced=0,
        interests=[],
        skills=[],
        lead_context={},
    )
    defaults.update(kwargs)
    return Contact(**defaults)


def _scalar_result(obj):
    """Build a mock session.execute() result that returns `obj` from scalar_one_or_none."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = obj
    return r


# ---------------------------------------------------------------------------
# get_contact — UUID validation
# ---------------------------------------------------------------------------

class TestGetContact:
    @pytest.mark.asyncio
    async def test_invalid_uuid_raises_value_error(self):
        """Non-UUID string must raise ValueError (→ 404), not DataError (→ 500)."""
        svc = ContactService(_make_session())
        with pytest.raises(ValueError, match="Contact not found"):
            await svc.get_contact("not-a-uuid")

    @pytest.mark.asyncio
    async def test_valid_uuid_not_found_raises_value_error(self):
        session = _make_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))
        svc = ContactService(session)
        with pytest.raises(ValueError, match="Contact not found"):
            await svc.get_contact(str(uuid4()))

    @pytest.mark.asyncio
    async def test_valid_uuid_found_returns_dict(self):
        contact = _make_contact()
        session = _make_session()
        session.execute = AsyncMock(return_value=_scalar_result(contact))
        svc = ContactService(session)
        result = await svc.get_contact(str(contact.id))
        assert result["id"] == str(contact.id)
        assert result["first_name"] == "Alice"

    @pytest.mark.asyncio
    async def test_empty_string_raises_value_error(self):
        svc = ContactService(_make_session())
        with pytest.raises(ValueError, match="Contact not found"):
            await svc.get_contact("")


# ---------------------------------------------------------------------------
# update_contact — UUID validation + field whitelist
# ---------------------------------------------------------------------------

class TestUpdateContact:
    @pytest.mark.asyncio
    async def test_invalid_uuid_raises_value_error(self):
        svc = ContactService(_make_session())
        with pytest.raises(ValueError, match="Contact not found"):
            await svc.update_contact("garbage", {"first_name": "Bob"})

    @pytest.mark.asyncio
    async def test_not_found_raises_value_error(self):
        session = _make_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))
        svc = ContactService(session)
        with pytest.raises(ValueError, match="Contact not found"):
            await svc.update_contact(str(uuid4()), {"first_name": "Bob"})

    @pytest.mark.asyncio
    async def test_allowed_fields_are_applied(self):
        contact = _make_contact()
        session = _make_session()
        session.execute = AsyncMock(return_value=_scalar_result(contact))
        svc = ContactService(session)
        result = await svc.update_contact(str(contact.id), {"first_name": "NewName", "company": "Acme"})
        assert contact.first_name == "NewName"
        assert contact.company == "Acme"
        assert contact.embedding_dirty is True

    @pytest.mark.asyncio
    async def test_disallowed_fields_are_ignored(self):
        """Internal fields like lead_score and is_lead must not be settable via update_contact."""
        contact = _make_contact()
        original_lead_score = contact.lead_score
        original_is_lead = contact.is_lead

        session = _make_session()
        session.execute = AsyncMock(return_value=_scalar_result(contact))
        svc = ContactService(session)

        await svc.update_contact(
            str(contact.id),
            {
                "first_name": "Bob",   # allowed
                "lead_score": 99.9,    # NOT allowed — internal
                "is_lead": True,       # NOT allowed — internal
                "id": str(uuid4()),    # NOT allowed — primary key
                "source": "hacked",   # NOT allowed — provenance
            },
        )

        assert contact.first_name == "Bob"
        assert contact.lead_score == original_lead_score, "lead_score must not be overwritten"
        assert contact.is_lead == original_is_lead, "is_lead must not be overwritten"

    @pytest.mark.asyncio
    async def test_sets_embedding_dirty_on_update(self):
        contact = _make_contact()
        contact.embedding_dirty = False
        session = _make_session()
        session.execute = AsyncMock(return_value=_scalar_result(contact))
        svc = ContactService(session)
        await svc.update_contact(str(contact.id), {"first_name": "X"})
        assert contact.embedding_dirty is True


# ---------------------------------------------------------------------------
# delete_contact — UUID validation
# ---------------------------------------------------------------------------

class TestDeleteContact:
    @pytest.mark.asyncio
    async def test_invalid_uuid_raises_value_error(self):
        svc = ContactService(_make_session())
        with pytest.raises(ValueError, match="Contact not found"):
            await svc.delete_contact("not-a-uuid-at-all")

    @pytest.mark.asyncio
    async def test_not_found_raises_value_error(self):
        session = _make_session()
        session.execute = AsyncMock(return_value=_scalar_result(None))
        svc = ContactService(session)
        with pytest.raises(ValueError, match="Contact not found"):
            await svc.delete_contact(str(uuid4()))

    @pytest.mark.asyncio
    async def test_deletes_and_flushes(self):
        contact = _make_contact()
        session = _make_session()
        session.execute = AsyncMock(return_value=_scalar_result(contact))
        svc = ContactService(session)
        await svc.delete_contact(str(contact.id))
        session.delete.assert_awaited_once_with(contact)
        session.flush.assert_awaited_once()


# ---------------------------------------------------------------------------
# _ALLOWED_UPDATE_FIELDS — whitelist completeness sanity check
# ---------------------------------------------------------------------------

class TestAllowedUpdateFields:
    def test_internal_fields_not_in_whitelist(self):
        disallowed = {"id", "lead_score", "is_lead", "source", "created_at", "updated_at",
                      "embedding", "embedding_dirty", "lead_context"}
        intersection = disallowed & _ALLOWED_UPDATE_FIELDS
        assert not intersection, f"Internal fields found in whitelist: {intersection}"

    def test_user_fields_in_whitelist(self):
        expected_user_fields = {"first_name", "last_name", "email", "phone", "company",
                                "position", "telegram_username", "notes"}
        missing = expected_user_fields - _ALLOWED_UPDATE_FIELDS
        assert not missing, f"Expected user fields missing from whitelist: {missing}"
