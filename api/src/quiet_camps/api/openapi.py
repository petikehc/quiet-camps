"""The OpenAPI document, committed so every change to the API contract shows in a diff."""

import json
from pathlib import Path

from quiet_camps.api.app import create_app
from quiet_camps.api.settings import Settings

# src/quiet_camps/api/openapi.py → api/openapi.json, read by web/ to generate its types.
OPENAPI_FILE = Path(__file__).resolve().parents[3] / "openapi.json"


def openapi_document() -> str:
    """The same text on every run: the experiments stay out whatever the environment says."""
    app = create_app(Settings(experiments=False))
    return json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
