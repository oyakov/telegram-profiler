#!/usr/bin/env python
"""Run Alembic migrations."""

import sys
import os
from alembic.config import Config
from alembic import command

def main():
    # Create alembic config
    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "alembic.ini"))

    # Run upgrade to head
    print("Running migrations...")
    try:
        command.upgrade(alembic_cfg, "head")
        print("✅ Migrations applied successfully!")
        return 0
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
