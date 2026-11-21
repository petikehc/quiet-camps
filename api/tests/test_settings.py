import pytest
from pydantic import ValidationError

from quiet_camps.api.app import create_app
from quiet_camps.api.settings import Settings
from quiet_camps.db.config import LOCAL_URL


def test_defaults_to_the_local_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert Settings().database_url == LOCAL_URL


def test_reads_database_url_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://someone@elsewhere/camps")

    assert Settings().database_url == "postgresql+psycopg://someone@elsewhere/camps"


def test_debug_is_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEBUG", raising=False)

    assert Settings().debug is False


def test_debug_reads_yes_as_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEBUG", "yes")

    assert Settings().debug is True


def test_rejects_a_debug_value_that_isnt_a_bool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEBUG", "maybe")

    with pytest.raises(ValidationError):
        Settings()


def test_create_app_uses_the_settings_it_is_given() -> None:
    settings = Settings(debug=True)

    app = create_app(settings)

    assert app.debug is True
    assert app.state.settings is settings
