import os
import sys
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


@pytest.fixture(scope="session")
def base_url() -> str:
    return os.environ.get("CRISIS_ROOM_BASE_URL", "http://127.0.0.1:7860")


@pytest.fixture(scope="session")
def fastapi_app():
    # Import lazily so tests can still run environment-only checks if needed.
    from server.app import app

    return app


@pytest.fixture()
def client(fastapi_app):
    from fastapi.testclient import TestClient

    return TestClient(fastapi_app)

