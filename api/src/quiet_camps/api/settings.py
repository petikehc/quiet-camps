from pydantic_settings import BaseSettings

from quiet_camps.db.config import LOCAL_URL


class Settings(BaseSettings):
    database_url: str = LOCAL_URL
    debug: bool = False
