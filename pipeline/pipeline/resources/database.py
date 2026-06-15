from contextlib import asynccontextmanager, contextmanager
from typing import AsyncIterator, Iterator

from dagster import ConfigurableResource
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker


class DatabaseResource(ConfigurableResource):
    """SQLAlchemy database resource for both sync (Alembic/bulk) and async (normal) use."""

    database_url: str
    database_url_sync: str

    def setup_for_execution(self, context) -> None:
        self._async_engine = create_async_engine(
            self.database_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
        self._sync_engine = create_engine(
            self.database_url_sync,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
        self._async_session_factory = sessionmaker(
            self._async_engine, class_=AsyncSession, expire_on_commit=False
        )
        self._sync_session_factory = sessionmaker(self._sync_engine)

    def teardown_after_execution(self, context) -> None:
        if hasattr(self, "_sync_engine"):
            self._sync_engine.dispose()

    @asynccontextmanager
    async def get_async_session(self) -> AsyncIterator[AsyncSession]:
        async with self._async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    @contextmanager
    def get_sync_session(self) -> Iterator[Session]:
        with self._sync_session_factory() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    def execute_sync(self, statement: str, params: dict | None = None) -> None:
        with self._sync_engine.connect() as conn:
            conn.execute(text(statement), params or {})
            conn.commit()
