import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure the API project root is on sys.path when running from repo root
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Import the FastAPI app
from app.main import app


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as c:
        yield c
