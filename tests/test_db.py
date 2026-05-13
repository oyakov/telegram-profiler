"""Database CRUD tests."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from src.db.models import Contact, Message, Setting


@pytest.mark.asyncio
async def test_create_contact(db_session):
    """Test creating a contact."""
    contact = Contact(
        first_name="Test",
        last_name="User",
        email="test_create@example.com",
        company="TestCorp",
        source="manual",
    )
    db_session.add(contact)
    await db_session.flush()

    assert contact.id is not None
    assert contact.embedding_dirty is True


@pytest.mark.asyncio
async def test_contact_query(db_session):
    """Test querying contacts."""
    for i in range(5):
        c = Contact(
            first_name=f"QueryUser{i}",
            last_name="Test",
            email=f"query_user{i}@test.com",
            source="manual",
        )
        db_session.add(c)
    await db_session.flush()

    result = await db_session.execute(
        select(Contact).where(Contact.first_name.like("QueryUser%"))
    )
    contacts = result.scalars().all()
    assert len(contacts) == 5


@pytest.mark.asyncio
async def test_contact_with_arrays(db_session):
    """Test contact with array fields."""
    contact = Contact(
        first_name="ArrayTest",
        last_name="Test",
        email="array_test@test.com",
        interests=["AI", "Python", "Docker"],
        skills=["FastAPI", "PostgreSQL"],
        source="manual",
    )
    db_session.add(contact)
    await db_session.flush()

    result = await db_session.execute(
        select(Contact).where(Contact.first_name == "ArrayTest")
    )
    c = result.scalar_one()
    assert "AI" in c.interests
    assert "FastAPI" in c.skills


@pytest.mark.asyncio
async def test_message_relationship(db_session):
    """Test contact-message relationship."""
    contact = Contact(first_name="MsgTest", last_name="Test", source="manual", email="msgtest@test.com")
    db_session.add(contact)
    await db_session.flush()

    from datetime import datetime, timezone
    msg = Message(
        contact_id=contact.id,
        source="telegram",
        content="Hello world",
        direction="incoming",
        timestamp=datetime.now(timezone.utc),
    )
    db_session.add(msg)
    await db_session.flush()

    assert msg.id is not None
    assert msg.contact_id == contact.id


@pytest.mark.asyncio
async def test_settings_crud(db_session):
    """Test settings service."""
    from src.core.config import SettingsService

    svc = SettingsService(db_session)

    # Set
    await svc.set("test_key_crud", "test_value", "string", "A test setting")
    await db_session.flush()

    # Get
    val = await svc.get("test_key_crud")
    assert val == "test_value"

    # Get with type
    await svc.set("test_int_crud", "42", "int")
    await db_session.flush()
    val = await svc.get("test_int_crud")
    assert val == 42

    # Get all
    all_settings = await svc.get_all()
    keys = [s["key"] for s in all_settings]
    assert "test_key_crud" in keys

@pytest.mark.asyncio
async def test_message_contact_association(db_session):
    """Test many-to-many message-contact association."""
    from src.db.models import MessageContact
    from datetime import datetime, timezone
    import uuid

    # 1. Create a channel contact and a buyer contact
    channel = Contact(first_name="Ads Channel", telegram_id="channel_123", source="telegram")
    buyer = Contact(first_name="Lead User", telegram_username="lead_user", source="telegram_ad")
    db_session.add_all([channel, buyer])
    await db_session.flush()

    # 2. Create a message from the channel
    msg = Message(
        contact_id=channel.id,
        source="telegram",
        content="Ad for @lead_user here!",
        direction="incoming",
        timestamp=datetime.now(timezone.utc),
        group_id="channel_123",
        group_name="Ads Channel"
    )
    db_session.add(msg)
    await db_session.flush()

    # 3. Create associations
    # Link as sender
    link1 = MessageContact(message_id=msg.id, contact_id=channel.id, role="sender")
    # Link as ad_buyer
    link2 = MessageContact(message_id=msg.id, contact_id=buyer.id, role="ad_buyer")
    db_session.add_all([link1, link2])
    await db_session.flush()

    # 4. Verify relationships
    # Get message with associations
    result = await db_session.execute(
        select(Message).where(Message.id == msg.id)
    )
    m = result.scalar_one()
    # (Note: need to load relationships if testing them, but checking MessageContact table is enough)
    
    # Check MessageContact table
    res = await db_session.execute(
        select(MessageContact).where(MessageContact.message_id == msg.id)
    )
    links = res.scalars().all()
    assert len(links) == 2
    roles = [l.role for l in links]
    assert "sender" in roles
    assert "ad_buyer" in roles

    # Check filtering by buyer
    res = await db_session.execute(
        select(Message)
        .join(Message.associated_contacts)
        .where(MessageContact.contact_id == buyer.id)
    )
    buyer_msgs = res.scalars().all()
    assert len(buyer_msgs) == 1
    assert buyer_msgs[0].id == msg.id
