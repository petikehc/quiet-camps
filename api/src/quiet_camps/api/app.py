from fastapi import FastAPI

from quiet_camps.api.health import health_router
from quiet_camps.api.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()
    app = FastAPI(debug=settings.debug)
    app.include_router(health_router)
    app.state.settings = settings

    return app
