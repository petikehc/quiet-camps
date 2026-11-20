from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from quiet_camps.api.db import get_session

health_router = APIRouter()


@health_router.get("/health")
async def health(
    session: Annotated[AsyncSession, Depends(get_session)], response: Response
) -> dict[str, str]:
    try:
        await session.execute(text("SELECT 1"))
    except OperationalError:
        response.status_code = 503
        return {"status": "error", "database": "unreachable"}
    return {"status": "ok", "database": "ok"}
