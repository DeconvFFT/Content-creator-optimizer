from pathlib import Path

from psycopg import AsyncConnection

from all_about_llms.config import Settings
from all_about_llms.orchestration.checkpointing import setup_postgres_checkpointer

ROOT = Path(__file__).resolve().parents[3]
FOUNDATION_SCHEMA = ROOT / "infra/postgres/001_foundation.sql"


async def apply_foundation_schema(settings: Settings) -> None:
    """Apply the application schema to Postgres.

    The schema is idempotent and assumes the configured database is Postgres
    with pgvector available. There is deliberately no SQLite compatibility path.
    """

    sql = FOUNDATION_SCHEMA.read_text(encoding="utf-8")
    async with await AsyncConnection.connect(settings.database_url, autocommit=True) as conn:
        await conn.execute(sql)


async def setup_durable_storage(settings: Settings) -> None:
    """Apply app migrations and LangGraph checkpoint migrations."""

    await apply_foundation_schema(settings)
    await setup_postgres_checkpointer(settings)
