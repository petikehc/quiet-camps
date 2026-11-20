from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from quiet_camps.api.health import health_router
from quiet_camps.api.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()
    app = FastAPI(debug=settings.debug)
    app.include_router(health_router)
    app.state.settings = settings
    app.state.engine = create_async_engine(settings.database_url)
    app.state.sessionmaker = async_sessionmaker(app.state.engine)

    return app
