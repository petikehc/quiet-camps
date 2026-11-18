import os

# The docker-compose database. Local only: the password is in docker-compose.yml too.
LOCAL_URL = "postgresql+psycopg://quiet_camps:quiet_camps@localhost:5432/quiet_camps"


def database_url() -> str:
    """DATABASE_URL if it's set (tests, deploys), otherwise the local database."""
    return os.environ.get("DATABASE_URL", LOCAL_URL)
