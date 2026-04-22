"""Excel/CSV connector — import contacts from spreadsheet files."""

from __future__ import annotations

import structlog
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.connectors.base import BaseConnector, SyncResult
from src.db.database import get_session
from src.db.models import Contact, SyncState

logger = structlog.get_logger()

# Common column name mappings
COLUMN_MAP = {
    # first_name
    "first_name": "first_name", "firstname": "first_name", "first": "first_name",
    "имя": "first_name", "name": "first_name",
    # last_name
    "last_name": "last_name", "lastname": "last_name", "last": "last_name",
    "surname": "last_name", "фамилия": "last_name",
    # company
    "company": "company", "organization": "company", "org": "company",
    "компания": "company", "организация": "company",
    # position
    "position": "position", "title": "position", "job_title": "position",
    "role": "position", "должность": "position",
    # email
    "email": "email", "e-mail": "email", "mail": "email",
    "электронная почта": "email", "почта": "email",
    # phone
    "phone": "phone", "telephone": "phone", "tel": "phone",
    "mobile": "phone", "телефон": "phone",
    # telegram
    "telegram": "telegram_username", "telegram_username": "telegram_username",
    "tg": "telegram_username", "телеграм": "telegram_username",
    # linkedin
    "linkedin": "linkedin_url", "linkedin_url": "linkedin_url",
    # notes
    "notes": "notes", "note": "notes", "comment": "notes",
    "comments": "notes", "заметки": "notes",
    # context
    "context": "context", "how_we_met": "context", "meeting": "context",
    "контекст": "context",
}


class ExcelConnector(BaseConnector):
    """Import contacts from Excel/CSV/TSV files."""

    name = "excel"

    def __init__(self, db_name: str | None = None):
        self.db_name = db_name or os.getenv('POSTGRES_DB', 'crm')

    async def sync(self, file_path: str | Path | None = None, **kwargs) -> SyncResult:
        """Import contacts from a file.

        Args:
            file_path: Path to the file. If None, scans uploads/ directory.
        """
        result = SyncResult(connector=self.name, started_at=datetime.now(timezone.utc))

        try:
            if file_path:
                files = [Path(file_path)]
            else:
                upload_dir = Path("/app/uploads")
                files = list(upload_dir.glob("*.xlsx")) + \
                        list(upload_dir.glob("*.xls")) + \
                        list(upload_dir.glob("*.csv")) + \
                        list(upload_dir.glob("*.tsv"))

            if not files:
                result.status = "success"
                result.metadata["message"] = "No files to import"
                return result

            async with get_session(db_name=self.db_name) as session:
                for f in files:
                    try:
                        created, updated = await self._import_file(session, f)
                        result.contacts_created += created
                        result.contacts_updated += updated
                    except Exception as e:
                        result.errors.append(f"{f.name}: {str(e)}")
                        logger.error("excel_import_error", file=f.name, error=str(e))

                await session.commit()

        except Exception as e:
            result.status = "error"
            result.errors.append(str(e))

        result.completed_at = datetime.now(timezone.utc)
        return result

    async def _import_file(self, session: AsyncSession, file_path: Path) -> tuple[int, int]:
        """Import a single file. Returns (created, updated) counts."""
        logger.info("excel_importing", file=file_path.name)

        # Read file
        suffix = file_path.suffix.lower()
        if suffix == ".csv":
            df = pd.read_csv(file_path)
        elif suffix == ".tsv":
            df = pd.read_csv(file_path, sep="\t")
        else:
            df = pd.read_excel(file_path)

        # Normalize column names
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

        # Map columns
        mapped_cols = {}
        for col in df.columns:
            if col in COLUMN_MAP:
                mapped_cols[col] = COLUMN_MAP[col]

        if not mapped_cols:
            raise ValueError(f"Could not auto-detect any contact columns in {file_path.name}")

        df = df.rename(columns=mapped_cols)
        logger.info("excel_columns_mapped", file=file_path.name, columns=list(mapped_cols.values()))

        created = 0
        updated = 0
        batch_size = 500

        for i in range(0, len(df), batch_size):
            batch = df.iloc[i : i + batch_size]
            for _, row in batch.iterrows():
                data = {k: v for k, v in row.to_dict().items() if pd.notna(v) and k in Contact.__table__.columns.keys()}

                if not data.get("first_name") and not data.get("email"):
                    continue  # Skip rows with no name or email

                # Check duplicate
                existing = None
                if data.get("email"):
                    res = await session.execute(
                        select(Contact).where(Contact.email == data["email"]).limit(1)
                    )
                    existing = res.scalar_one_or_none()

                if not existing and data.get("phone"):
                    res = await session.execute(
                        select(Contact).where(Contact.phone == data["phone"]).limit(1)
                    )
                    existing = res.scalar_one_or_none()

                if existing:
                    # Merge new data
                    for field, val in data.items():
                        if not getattr(existing, field, None) and val:
                            setattr(existing, field, val)
                    existing.embedding_dirty = True
                    updated += 1
                else:
                    contact = Contact(**data, source="excel", embedding_dirty=True)
                    session.add(contact)
                    created += 1

            await session.flush()

        logger.info("excel_imported", file=file_path.name, created=created, updated=updated)
        return created, updated

    async def get_status(self) -> dict[str, Any]:
        async with get_session(db_name=self.db_name) as session:
            result = await session.execute(
                select(SyncState).where(SyncState.connector == self.name)
            )
            state = result.scalar_one_or_none()
            return {
                "connector": self.name,
                "status": state.status if state else "idle",
                "last_sync_at": state.last_sync_at.isoformat() if state and state.last_sync_at else None,
            }

    async def test_connection(self) -> bool:
        """Excel connector is always 'connectable' — just checks uploads dir exists."""
        return Path("/app/uploads").exists()
