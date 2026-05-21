import pytest
from datetime import datetime, timezone
from src.db.models import Contact, Message, TrackedFolder, TrackedChannel

@pytest.mark.asyncio(loop_scope="session")
async def test_tracking_channels_messages_count(api_client, db_session):
    # 1. Create a folder
    folder = TrackedFolder(name="Folder BG Intel")
    db_session.add(folder)
    await db_session.flush()

    # 2. Create two channels belonging to this folder
    chan1 = TrackedChannel(
        folder_id=folder.id,
        telegram_id="111",
        title="Channel One",
        entity_type="channel"
    )
    chan2 = TrackedChannel(
        folder_id=folder.id,
        telegram_id="222",
        title="Channel Two",
        entity_type="channel"
    )
    db_session.add_all([chan1, chan2])
    await db_session.flush()

    # 3. Create a contact to be the sender
    sender = Contact(first_name="Sender", source="telegram")
    db_session.add(sender)
    await db_session.flush()

    # 4. Create messages in the channels
    # Channel 1: 3 messages
    for i in range(3):
        msg = Message(
            contact_id=sender.id,
            folder_id=folder.id,
            source="telegram",
            source_message_id=f"111_{i}",
            content=f"Message {i} in channel 1",
            group_id="111",
            group_name="Channel One",
            timestamp=datetime.now(timezone.utc)
        )
        db_session.add(msg)

    # Channel 2: 1 message
    msg2 = Message(
        contact_id=sender.id,
        folder_id=folder.id,
        source="telegram",
        source_message_id="222_0",
        content="Message in channel 2",
        group_id="222",
        group_name="Channel Two",
        timestamp=datetime.now(timezone.utc)
    )
    db_session.add(msg2)
    await db_session.flush()
    await db_session.commit()

    # 5. Call the /api/tracking/channels endpoint
    response = await api_client.get("/api/tracking/channels", headers={"X-Database": "crm_test"})
    assert response.status_code == 200

    data = response.json()
    channels = data["channels"]
    
    # Map by telegram_id
    chan_map = {c["telegram_id"]: c for c in channels if c["telegram_id"] in ["111", "222"]}
    assert len(chan_map) == 2

    # Under the old buggy code, both would show messages_count = 4 (the folder count).
    # Under the fixed code, they must show their respective counts: 3 and 1!
    assert chan_map["111"]["messages_count"] == 3
    assert chan_map["222"]["messages_count"] == 1
