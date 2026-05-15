import asyncio
from celery import Task
from src.db.database import get_session

class AsyncDBTask(Task):
    """Base class for Celery tasks that need to run async coroutines with DB session support."""
    
    _loop = None

    @property
    def loop(self):
        if self._loop is None or self._loop.is_closed():
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop

    def run_async(self, coro):
        """Helper to run a coroutine in the task's event loop."""
        return self.loop.run_until_complete(coro)

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
