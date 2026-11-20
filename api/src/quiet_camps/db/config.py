import os

from sqlalchemy import make_url

# The docker-compose database. Local only: the password is in docker-compose.yml too.
LOCAL_URL = "postgresql+psycopg://quiet_camps:quiet_camps@localhost:5432/quiet_camps"


def database_url() -> str:
    """DATABASE_URL if it's set (tests, deploys), otherwise the local database."""
    return os.environ.get("DATABASE_URL", LOCAL_URL)


def psycopg_conninfo() -> str:
    """The same database for psycopg.connect(), which doesn't know SQLAlchemy's '+psycopg'."""
    url = make_url(database_url()).set(drivername="postgresql")
    return url.render_as_string(hide_password=False)
