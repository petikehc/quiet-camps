from datetime import date

import psycopg
import pytest
from psycopg.rows import TupleRow
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from quiet_camps.api.queries import search_quiet
from quiet_camps.api.settings import Settings


@pytest.mark.anyio
async def test_search_runs_against_the_migrated_schema(
    conn: psycopg.Connection[TupleRow], api_settings: Settings
) -> None:
    engine = create_async_engine(api_settings.database_url)
    async with async_sessionmaker(engine)() as session:
        found = await search_quiet(session, date(2027, 3, 26), date(2027, 3, 29), None, None, 10)
    await engine.dispose()

    assert found == []
