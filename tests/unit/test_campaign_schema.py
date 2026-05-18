"""Unit tests for campaign Pydantic schemas — message length caps and sample_contact sanitization."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.api.schemas.campaigns import CampaignPreviewRequest, CampaignCreate


# ---------------------------------------------------------------------------
# CampaignPreviewRequest — message length and sample_contact sanitization
# ---------------------------------------------------------------------------

class TestCampaignPreviewRequest:
    def test_accepts_valid_request(self):
        req = CampaignPreviewRequest(
            message="Hello {first_name}!",
            sample_contact={"first_name": "Alice", "company": "Acme"},
        )
        assert req.message == "Hello {first_name}!"
        assert req.sample_contact["first_name"] == "Alice"

    def test_rejects_message_exceeding_max_length(self):
        with pytest.raises(ValidationError):
            CampaignPreviewRequest(message="x" * 4097)

    def test_accepts_message_at_max_length(self):
        req = CampaignPreviewRequest(message="x" * 4096)
        assert len(req.message) == 4096

    def test_strips_unknown_keys_from_sample_contact(self):
        """Keys not in the whitelist must be removed."""
        req = CampaignPreviewRequest(
            message="Hi",
            sample_contact={
                "first_name": "Bob",
                "__class__": "evil",        # injection attempt
                "unknown_field": "value",
            },
        )
        assert "first_name" in req.sample_contact
        assert "__class__" not in req.sample_contact
        assert "unknown_field" not in req.sample_contact

    def test_caps_value_length_in_sample_contact(self):
        long_value = "A" * 1000
        req = CampaignPreviewRequest(
            message="Hi",
            sample_contact={"first_name": long_value},
        )
        assert len(req.sample_contact["first_name"]) <= 255

    def test_empty_sample_contact_is_fine(self):
        req = CampaignPreviewRequest(message="Hello")
        assert req.sample_contact == {}

    def test_rejects_empty_message(self):
        with pytest.raises(ValidationError):
            CampaignPreviewRequest(message="")


# ---------------------------------------------------------------------------
# CampaignCreate — message length
# ---------------------------------------------------------------------------

class TestCampaignCreate:
    def test_rejects_message_exceeding_max_length(self):
        with pytest.raises(ValidationError):
            CampaignCreate(
                name="Test",
                message="x" * 4097,
                contact_ids=[],
            )

    def test_accepts_message_at_max_length(self):
        from uuid import uuid4
        req = CampaignCreate(
            name="Test",
            message="x" * 4096,
            contact_ids=[uuid4()],
        )
        assert len(req.message) == 4096

    def test_rejects_name_exceeding_max_length(self):
        with pytest.raises(ValidationError):
            CampaignCreate(
                name="n" * 256,
                message="Hello",
                contact_ids=[],
            )
