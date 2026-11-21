from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from quiet_camps.api.campgrounds import campground_router
from quiet_camps.api.experiment import experiment_router
from quiet_camps.api.health import health_router
from quiet_camps.api.problems import add_problem_handlers
from quiet_camps.api.search import search_router
from quiet_camps.api.settings import Settings
from quiet_camps.api.year import year_router


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()
    app = FastAPI(debug=settings.debug)
    # Only when the client accepts gzip; a small response gains nothing.
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    add_problem_handlers(app)
    app.include_router(health_router)
    # Routes match in the order added: /campgrounds/{campground_id} would claim /campgrounds/quiet.
    app.include_router(search_router)
    app.include_router(campground_router)
    app.include_router(year_router)
    if settings.experiments:
        app.include_router(experiment_router)
    app.state.settings = settings
    app.state.engine = create_async_engine(settings.database_url)
    app.state.sessionmaker = async_sessionmaker(app.state.engine)

    return app
