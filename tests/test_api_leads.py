"""Tests for the Leads API endpoints."""

from __future__ import annotations
import pytest
from sqlalchemy import delete
from src.db.models import Contact

@pytest.mark.asyncio
async def test_list_leads_pagination(api_client, db_session):
    """Test pagination on the /leads/top endpoint."""
    # 1. Cleanup and Prepare test data
    await db_session.execute(delete(Contact).where(Contact.source == "__api_test__"))
    await db_session.commit()

    for i in range(15):
        c = Contact(
            first_name=f"Lead {i:02d}",
            telegram_username=f"lead_{i:02d}",
            is_lead=True,
            lead_score=100.0 + float(i),
            source="__api_test__"
        )
        db_session.add(c)
    await db_session.commit()

    # 2. Test first page
    response = await api_client.get("/api/leads/top?page=1&page_size=10&min_score=100")
    assert response.status_code == 200
    data = response.json()
    assert len(data["contacts"]) == 10
    assert data["total"] == 15
    assert data["page"] == 1
    assert data["page_size"] == 10
    # Highest score should be first (lead 14, score 114)
    assert data["contacts"][0]["first_name"] == "Lead 14"

    # 3. Test second page
    response = await api_client.get("/api/leads/top?page=2&page_size=10&min_score=100")
    assert response.status_code == 200
    data = response.json()
    assert len(data["contacts"]) == 5
    assert data["page"] == 2
    # Should be lead 04 (score 104) down to 00 (score 100)
    assert data["contacts"][0]["first_name"] == "Lead 04"

    # 4. Cleanup
    await db_session.execute(delete(Contact).where(Contact.source == "__api_test__"))
    await db_session.commit()
