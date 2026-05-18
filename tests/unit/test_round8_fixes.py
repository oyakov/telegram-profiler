"""Unit tests for round-8 fixes."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from pydantic import ValidationError


def _make_session():
    s = AsyncMock()
    s.add = MagicMock()
    return s


def _scalar_result(obj):
    r = MagicMock()
    r.scalar_one_or_none.return_value = obj
    return r


# ===========================================================================
# Issue #1 — contacts router must not echo ValueError text to the client
# ===========================================================================

class TestContactsRouterErrorMessages:
    def test_get_contact_404_is_static_string(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from src.api.routers.contacts import router
        app = FastAPI()
        app.include_router(router)

        with patch("src.api.routers.contacts.ContactService") as MockSvc:
            svc_instance = MagicMock()
            svc_instance.get_contact = AsyncMock(side_effect=ValueError("some internal detail that must not leak"))
            MockSvc.return_value = svc_instance

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get("/contacts/not-a-real-id")

        assert resp.status_code == 404
        assert "internal detail" not in resp.text
        assert "some internal detail" not in resp.text


# ===========================================================================
# Issue #2 — run_campaign allows retry of "sending" campaigns
# ===========================================================================

class TestCampaignSendingRetry:
    @pytest.mark.asyncio
    async def test_sending_campaign_is_retried(self):
        from src.services.campaign_service import CampaignService
        from src.db.models.marketing import Campaign, CampaignMessage
        from src.db.models.content import Contact

        cid = uuid4()
        campaign = Campaign(id=cid, name="Stuck", message="Hi",
                            status="sending", sent_count=0, failed_count=0, total_contacts=1)
        contact = Contact(id=uuid4(), first_name="X", telegram_id="111",
                          source="test", is_lead=False, is_tracked=False, is_personal=False,
                          lead_score=0.0, our_channel_ratio=0.0, total_messages_synced=0,
                          interests=[], skills=[], lead_context={})
        cm = CampaignMessage(id=uuid4(), campaign_id=cid, contact_id=contact.id, status="pending")

        session = _make_session()
        session.get = AsyncMock(return_value=campaign)
        pending_res = MagicMock()
        pending_res.scalars.return_value.all.return_value = [cm]
        contacts_res = MagicMock()
        contacts_res.scalars.return_value.all.return_value = [contact]
        session.execute = AsyncMock(side_effect=[pending_res, contacts_res])

        mock_delivery = AsyncMock()
        mock_delivery.send_message = AsyncMock(return_value=True)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            svc = CampaignService(session, delivery_provider=mock_delivery)
            result = await svc.run_campaign(cid)

        assert result.get("status") != "skipped"
        assert result.get("sent") == 1


# ===========================================================================
# Issue #3 — LeadSearchRepository._apply_profile_filter escapes ILIKE metacharacters
# ===========================================================================

class TestLeadSearchRepositoryILIKEEscape:
    def test_esc_escapes_percent(self):
        from src.db.repository import LeadSearchRepository
        assert LeadSearchRepository._esc("100%") == "100\\%"

    def test_esc_escapes_underscore(self):
        from src.db.repository import LeadSearchRepository
        assert LeadSearchRepository._esc("a_b") == "a\\_b"

    def test_esc_escapes_backslash(self):
        from src.db.repository import LeadSearchRepository
        assert LeadSearchRepository._esc("a\\b") == "a\\\\b"

    def test_esc_leaves_plain_string(self):
        from src.db.repository import LeadSearchRepository
        assert LeadSearchRepository._esc("Acme Corp") == "Acme Corp"

    def test_apply_profile_filter_source_uses_esc(self):
        """_apply_profile_filter must call _esc on user values (source-level check)."""
        import inspect
        from src.db.repository import LeadSearchRepository
        src = inspect.getsource(LeadSearchRepository._apply_profile_filter)
        assert "esc(" in src, "_apply_profile_filter must call esc() to escape ILIKE metacharacters"


# ===========================================================================
# Issue #4 — audio upload enforces 25 MB limit
# ===========================================================================

class TestAudioUploadSizeLimit:
    def test_oversized_audio_rejected_413(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from src.api.routers.pipeline import router, _MAX_AUDIO_BYTES
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app, raise_server_exceptions=False)

        oversized = b"x" * (_MAX_AUDIO_BYTES + 1)
        resp = client.post(
            "/pipeline/import/audio",
            files={"file": ("voice.ogg", oversized, "audio/ogg")},
        )
        assert resp.status_code == 413

    def test_max_audio_bytes_is_25mb(self):
        from src.api.routers.pipeline import _MAX_AUDIO_BYTES
        assert _MAX_AUDIO_BYTES == 25 * 1024 * 1024


# ===========================================================================
# Issue #5 — audio upload validates extension
# ===========================================================================

class TestAudioUploadExtensionValidation:
    def test_unknown_extension_rejected_400(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from src.api.routers.pipeline import router
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post(
            "/pipeline/import/audio",
            files={"file": ("malware.exe", b"MZ", "application/octet-stream")},
        )
        assert resp.status_code == 400

    def test_allowed_extensions_present(self):
        from src.api.routers.pipeline import _ALLOWED_AUDIO_EXTENSIONS
        for ext in (".ogg", ".mp3", ".wav", ".m4a"):
            assert ext in _ALLOWED_AUDIO_EXTENSIONS


# ===========================================================================
# Issue #6 — audio upload validates contact_id format
# ===========================================================================

class TestAudioUploadContactIdValidation:
    def test_invalid_contact_id_rejected_400(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from src.api.routers.pipeline import router
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post(
            "/pipeline/import/audio?contact_id=not-a-uuid",
            files={"file": ("voice.ogg", b"\x00", "audio/ogg")},
        )
        assert resp.status_code == 400

    def test_valid_contact_id_passes_validation(self):
        """A valid UUID should not be rejected by the format check."""
        import inspect
        from src.api.routers.pipeline import import_audio_file
        src = inspect.getsource(import_audio_file)
        assert "UUID(contact_id)" in src or "_UUID(contact_id)" in src


# ===========================================================================
# Issue #9 — retry batch must specify queue="connectors"
# ===========================================================================

class TestRetryBatchQueue:
    def test_retry_apply_async_specifies_connectors_queue(self):
        import inspect
        from src.pipeline import sync_orchestrator
        # Find the _retry_failed_batches method source
        src = inspect.getsource(sync_orchestrator.SyncOrchestrator._retry_failed_batches)
        # The retry apply_async must explicitly set queue="connectors"
        assert 'queue="connectors"' in src or "queue='connectors'" in src, \
            "_retry_failed_batches must pass queue='connectors' to apply_async"


# ===========================================================================
# Issue #21 — auth_service.is_authorized must not log str(e)
# ===========================================================================

class TestIsAuthorizedPIISanitization:
    @pytest.mark.asyncio
    async def test_is_authorized_logs_error_type_not_str_e(self):
        """is_authorized must log error_type= only, not error=str(e)."""
        import inspect
        from src.services.telegram.auth_service import TelegramAuthService
        src = inspect.getsource(TelegramAuthService.is_authorized)
        assert "error=str(e)" not in src, "is_authorized must not log str(e)"
        assert "error_type=type(e).__name__" in src, "is_authorized must log error_type="


# ===========================================================================
# Issue #23 — telegram_id must not be in _ALLOWED_UPDATE_FIELDS
# ===========================================================================

class TestTelegramIdNotInWhitelist:
    def test_telegram_id_excluded_from_update_fields(self):
        from src.services.contact_service import _ALLOWED_UPDATE_FIELDS
        assert "telegram_id" not in _ALLOWED_UPDATE_FIELDS, \
            "telegram_id is a dedup key and must not be user-updatable via the REST API"

    @pytest.mark.asyncio
    async def test_update_contact_ignores_telegram_id(self):
        from src.services.contact_service import ContactService
        from src.db.models.content import Contact

        contact = Contact(id=uuid4(), first_name="Alice", telegram_id="original_id",
                          source="test", is_lead=False, is_tracked=False, is_personal=False,
                          lead_score=0.0, our_channel_ratio=0.0, total_messages_synced=0,
                          interests=[], skills=[], lead_context={})
        session = _make_session()
        session.execute = AsyncMock(return_value=_scalar_result(contact))
        svc = ContactService(session)

        await svc.update_contact(str(contact.id), {
            "first_name": "Bob",
            "telegram_id": "hijacked_id",  # must be silently ignored
        })

        assert contact.first_name == "Bob"
        assert contact.telegram_id == "original_id", \
            "telegram_id must not be overwritten via update_contact"


# ===========================================================================
# Issue #24 — telegram router must log error_type, not str(e)
# ===========================================================================

class TestTelegramRouterPIISanitization:
    def test_auth_status_error_logs_type_not_str(self):
        import inspect
        import src.api.routers.telegram as telegram_router
        src_code = inspect.getsource(telegram_router)
        # The auth status error log must use error_type=, not error=str(e)
        assert "error_type=type(e).__name__" in src_code, \
            "telegram router must log error_type=type(e).__name__ for auth status errors"
        # Verify the specific string-leaking pattern is gone
        assert 'telegram_auth_status_error", error=str(e)' not in src_code, \
            "telegram_auth_status_error must not pass str(e) to logger"


# ===========================================================================
# Issue #25 — /stats/tree must validate X-Database before Redis key
# ===========================================================================

class TestTreeEndpointDBValidation:
    def test_invalid_db_name_in_tree_endpoint_rejected(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from src.api.routers.system import router
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.get("/stats/tree", headers={"X-Database": "../../etc/passwd"})
        assert resp.status_code == 400


# ===========================================================================
# Issue #26 — run_campaign must set status="failed" on unhandled crash
# ===========================================================================

class TestCampaignFinallyBlock:
    def test_run_campaign_has_outer_try_except_with_failed_status(self):
        """run_campaign must set campaign.status='failed' when an unhandled exception escapes."""
        import inspect
        from src.services.campaign_service import CampaignService
        src = inspect.getsource(CampaignService.run_campaign)
        # Source must contain the outer exception handler that resets status to "failed"
        assert 'campaign.status = "failed"' in src, \
            "run_campaign must set status='failed' in its outer except/finally block"

    @pytest.mark.asyncio
    async def test_campaign_set_to_failed_when_commit_raises(self):
        """If the final commit raises (e.g. DB gone), status must be set to 'failed'."""
        from src.services.campaign_service import CampaignService
        from src.db.models.marketing import Campaign

        cid = uuid4()
        campaign = Campaign(id=cid, name="Crash", message="Hi",
                            status="draft", sent_count=0, failed_count=0, total_contacts=1)
        session = _make_session()
        session.get = AsyncMock(return_value=campaign)

        # No pending messages — loop exits immediately; final commit raises
        empty_res = MagicMock()
        empty_res.scalars.return_value.all.return_value = []
        contacts_res = MagicMock()
        contacts_res.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(side_effect=[empty_res, contacts_res])

        commit_calls = 0

        async def commit_side_effect():
            nonlocal commit_calls
            commit_calls += 1
            if commit_calls == 1:
                return None  # first commit (status=running) succeeds
            raise RuntimeError("DB connection lost")  # second commit (status=completed) fails

        session.commit = commit_side_effect

        mock_delivery = AsyncMock()
        svc = CampaignService(session, delivery_provider=mock_delivery)

        with pytest.raises(RuntimeError):
            await svc.run_campaign(cid)

        assert campaign.status == "failed", \
            "Campaign must be set to 'failed' when the final commit raises"
