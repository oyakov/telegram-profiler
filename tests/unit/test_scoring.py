import pytest
from datetime import datetime, timezone, timedelta
from src.pipeline.unified_processor import _update_lead_scores_impl
from src.db.models import Contact
from unittest.mock import AsyncMock, MagicMock, patch


def _mock_session(contacts: list) -> AsyncMock:
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = contacts
    mock_session.execute.return_value = mock_result
    return mock_session


def _mock_settings_service(session):
    """Patch SettingsService.get to return deterministic defaults."""
    svc = AsyncMock()
    svc.get = AsyncMock(side_effect=[
        ['dev', 'invest', 'agency', 'partnership', 'ai', 'software', 'hiring'],  # HIGH_VALUE_KEYWORDS
        "1753396658",  # OUR_CHANNEL_ID
        5.0,           # KW_BONUS
        3.0,           # MULT_WEEK
        2.0,           # MULT_MONTH
    ])
    return svc


@pytest.mark.asyncio
async def test_lead_scoring_recent_high_value():
    """Recent entry with a high-value keyword should score highest."""
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=2)
    month_ago = now - timedelta(days=15)

    contact = Contact(
        id="test-contact",
        is_lead=True,
        lead_context={
            "lead_history": [
                {
                    "timestamp": week_ago.isoformat(),
                    "summary": "Looking for a dev for a new software project",
                    "quality": 5,
                    "group_id": "123"
                },
                {
                    "timestamp": month_ago.isoformat(),
                    "summary": "General interest",
                    "quality": 3,
                    "group_id": "1753396658"  # OUR_CHANNEL_ID
                }
            ]
        }
    )

    mock_session = _mock_session([contact])

    with patch("src.pipeline.unified_processor.SettingsService", return_value=_mock_settings_service(mock_session)):
        await _update_lead_scores_impl(mock_session)

    # Entry 1: base=1.0 * MULT_WEEK=3.0 + KW_BONUS=5.0 → 8.0 * quality=5/5 = 8.0
    # Entry 2: base=1.0 * MULT_MONTH=2.0 + 0 → 2.0 * quality=3/5 = 1.2
    assert contact.lead_score == 9.2
    # Entry 2 is in OUR_CHANNEL_ID → 1/2 = 50%
    assert contact.our_channel_ratio == 50.0


@pytest.mark.asyncio
async def test_lead_scoring_empty_history():
    """Contact with no lead history should get score=0 and ratio=0."""
    contact = Contact(
        id="no-history",
        is_lead=True,
        lead_context={"lead_history": []}
    )

    mock_session = _mock_session([contact])

    with patch("src.pipeline.unified_processor.SettingsService", return_value=_mock_settings_service(mock_session)):
        await _update_lead_scores_impl(mock_session)

    assert contact.lead_score == 0.0
    assert contact.our_channel_ratio == 0.0


@pytest.mark.asyncio
async def test_lead_scoring_old_entries_use_default_multiplier():
    """Entries older than 30 days use no recency multiplier (base=1.0)."""
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=45)

    contact = Contact(
        id="old-entry",
        is_lead=True,
        lead_context={
            "lead_history": [
                {
                    "timestamp": old.isoformat(),
                    "summary": "Looking to hire",
                    "quality": 5,
                    "group_id": "999"
                }
            ]
        }
    )

    mock_session = _mock_session([contact])

    with patch("src.pipeline.unified_processor.SettingsService", return_value=_mock_settings_service(mock_session)):
        await _update_lead_scores_impl(mock_session)

    # base=1.0 (no recency mult), no keyword match, quality=5/5=1.0 → score=1.0
    assert contact.lead_score == 1.0
    assert contact.our_channel_ratio == 0.0


@pytest.mark.asyncio
async def test_lead_scoring_our_channel_ratio_all_entries():
    """All entries in OUR_CHANNEL_ID → ratio=100%."""
    now = datetime.now(timezone.utc)
    recent = now - timedelta(days=1)

    contact = Contact(
        id="all-ours",
        is_lead=True,
        lead_context={
            "lead_history": [
                {"timestamp": recent.isoformat(), "summary": "ping", "quality": 5, "group_id": "1753396658"},
                {"timestamp": recent.isoformat(), "summary": "pong", "quality": 5, "group_id": "1753396658"},
            ]
        }
    )

    mock_session = _mock_session([contact])

    with patch("src.pipeline.unified_processor.SettingsService", return_value=_mock_settings_service(mock_session)):
        await _update_lead_scores_impl(mock_session)

    assert contact.our_channel_ratio == 100.0


@pytest.mark.asyncio
async def test_lead_scoring_multiple_contacts_scored_independently():
    """Each contact in the result set receives its own independent score."""
    now = datetime.now(timezone.utc)
    recent = now - timedelta(days=1)
    old = now - timedelta(days=60)

    high = Contact(
        id="high",
        is_lead=True,
        lead_context={"lead_history": [{"timestamp": recent.isoformat(), "summary": "ai project", "quality": 5, "group_id": "1"}]}
    )
    low = Contact(
        id="low",
        is_lead=True,
        lead_context={"lead_history": [{"timestamp": old.isoformat(), "summary": "nothing", "quality": 1, "group_id": "2"}]}
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [high, low]
    mock_session = AsyncMock()
    mock_session.execute.return_value = mock_result

    # Need fresh side_effect list for two contacts
    svc = AsyncMock()
    svc.get = AsyncMock(side_effect=[
        ['dev', 'invest', 'agency', 'partnership', 'ai', 'software', 'hiring'],
        "1753396658",
        5.0,
        3.0,
        2.0,
    ])
    with patch("src.pipeline.unified_processor.SettingsService", return_value=svc):
        await _update_lead_scores_impl(mock_session)

    # high: 1.0 * 3.0 (week) + 5.0 (ai keyword) * 1.0 (quality 5/5) = 8.0
    assert high.lead_score == 8.0
    # low: 1.0 (no mult, >30d) + 0 (no kw) * 0.2 (quality 1/5) = 0.2
    assert low.lead_score == 0.2
