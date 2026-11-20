from fastapi import FastAPI

from quiet_camps.api.health import health_router


def create_app() -> FastAPI:
    app = FastAPI()
    app.include_router(health_router)
    return app
