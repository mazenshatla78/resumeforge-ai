import os
import sys
import tempfile

# Use a temp sqlite db for tests
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_tmp, "test.db").replace("\\", "/")
os.environ["JWT_SECRET"] = "test-secret-key-for-tests-only"
os.environ["GROQ_API_KEY"] = ""
os.environ["ADMIN_BOOTSTRAP_SECRET"] = "test-bootstrap-secret"
os.environ["RATE_LIMIT_AUTH"] = "1000/minute"
os.environ["RATE_LIMIT_AI"] = "1000/minute"
os.environ["ALLOWED_ORIGINS"] = "http://testserver"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import init_db, Base, engine
init_db()

import pytest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture(autouse=True)
def _reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    r = client.post("/api/auth/register", json={"email": "user@test.com", "password": "password123", "name": "User"})
    assert r.status_code == 200
    token = r.json()["token"]
    return {"Authorization": f"Bearer {token}"}, r.json()


@pytest.fixture
def second_user(client):
    r = client.post("/api/auth/register", json={"email": "other@test.com", "password": "password123", "name": "Other"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}, r.json()
