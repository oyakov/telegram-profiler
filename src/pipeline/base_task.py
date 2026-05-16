import asyncio
from celery import Task
from src.db.database import get_session

class AsyncDBTask(Task):
    """Base class for Celery tasks that need to run async coroutines with DB session support.

    Each call to run_async() creates a *fresh* event loop and tears it down afterwards.
    This avoids the class-level loop sharing bug (a closed/broken loop from one task
    poisoning subsequent tasks in the same Celery worker process).
    """

    def run_async(self, coro):
        """Run a coroutine in a fresh event loop; always cleans up on exit."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            try:
                # Drain any remaining async generators before closing
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception:
                pass
            loop.close()
            asyncio.set_event_loop(None)

    def get_db_name(self, *args, **kwargs):
        """Extract db_name from args or kwargs, defaulting to 'crm'."""
        db_name = kwargs.get('db_name')
        if not db_name and args:
            # Assume db_name might be a positional arg if it's a string and looks like a DB name
            # This is a heuristic, better to use kwargs
            pass
        from src.core.config import get_settings
        return db_name or get_settings().postgres_db

    async def session_scope(self, db_name=None):
        """Shortcut for getting an async session."""
        return get_session(db_name=db_name or self.get_db_name())
