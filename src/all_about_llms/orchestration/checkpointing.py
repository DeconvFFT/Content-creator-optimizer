from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from all_about_llms.config import Settings


@asynccontextmanager
async def postgres_checkpointer(
    settings: Settings,
) -> AsyncIterator[AsyncPostgresSaver]:
    """Create a LangGraph Postgres checkpointer for durable graph state."""

    async with AsyncPostgresSaver.from_conn_string(
        settings.database_url,
        pipeline=False,
    ) as saver:
        yield saver


async def setup_postgres_checkpointer(settings: Settings) -> None:
    """Create or upgrade LangGraph checkpoint tables in Postgres."""

    async with postgres_checkpointer(settings) as saver:
        await saver.setup()
