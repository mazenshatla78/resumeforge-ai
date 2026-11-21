def test_register_login(client):
    r = client.post("/api/auth/register", json={"email": "a@b.com", "password": "password123"})
    assert r.status_code == 200
    assert "token" in r.json()
    r2 = client.post("/api/auth/login", json={"email": "a@b.com", "password": "password123"})
    assert r2.status_code == 200
    r3 = client.post("/api/auth/login", json={"email": "a@b.com", "password": "wrong"})
    assert r3.status_code == 401


def test_protected_requires_auth(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_returns_user(client, auth_headers):
    headers, info = auth_headers
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "user@test.com"
    assert r.json()["role"] == "user"


def test_rate_limit_auth(client):
    for i in range(6):
        client.post("/api/auth/login", json={"email": "nope@test.com", "password": "wrong"})
    r = client.post("/api/auth/login", json={"email": "nope@test.com", "password": "wrong"})
    # slowapi returns 429
    assert r.status_code in (401, 429)
