"""AsyncSession management and transaction-scoped RLS context propagation."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def set_rls_context(session: AsyncSession, user_id: UUID) -> None:
    """Set transaction-scoped session configuration for PostgreSQL Row-Level Security.

    The third parameter `is_local = true` ensures the setting applies only to the
    current transaction and is automatically cleared upon COMMIT or ROLLBACK.
    """
    await session.execute(
        text("SELECT set_config('app.current_user_id', :user_id, true)"),
        {"user_id": str(user_id)},
    )


async def clear_rls_context(session: AsyncSession) -> None:
    """Explicitly reset the transaction-scoped RLS user setting."""
    await session.execute(text("SELECT set_config('app.current_user_id', '', true)"))


@asynccontextmanager
async def transactional_session(
    session_factory: async_sessionmaker[AsyncSession],
    user_id: UUID | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional AsyncSession scope with optional RLS context."""
    async with session_factory() as session, session.begin():
        if user_id is not None:
            await set_rls_context(session, user_id)
        yield session
