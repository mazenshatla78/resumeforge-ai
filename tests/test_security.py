def test_resume_ownership(client, auth_headers, second_user):
    headers, info = auth_headers
    other_headers, other_info = second_user
    # user creates resume
    r = client.post("/api/resumes", json={"title": "Mine", "content": "content here"}, headers=headers)
    assert r.status_code == 200
    rid = r.json()["id"]
    # other cannot read
    r2 = client.get(f"/api/resumes/{rid}", headers=other_headers)
    assert r2.status_code == 404
    # other cannot delete
    r3 = client.delete(f"/api/resumes/{rid}", headers=other_headers)
    assert r3.status_code == 404
    # owner can read
    r4 = client.get(f"/api/resumes/{rid}", headers=headers)
    assert r4.status_code == 200


def test_admin_endpoints_forbidden_for_user(client, auth_headers):
    headers, info = auth_headers
    r = client.get("/api/admin/overview", headers=headers)
    assert r.status_code == 403


def test_bootstrap_admin(client):
    r = client.post("/api/admin/bootstrap", json={
        "secret": "test-bootstrap-secret", "username": "admin", "password": "adminpass123", "name": "Admin"
    })
    assert r.status_code == 200
    # second bootstrap fails
    r2 = client.post("/api/admin/bootstrap", json={
        "secret": "test-bootstrap-secret", "username": "admin2", "password": "adminpass123"
    })
    assert r2.status_code == 403


def test_admin_login_and_access(client):
    client.post("/api/admin/bootstrap", json={
        "secret": "test-bootstrap-secret", "username": "admin", "password": "adminpass123", "name": "Admin"
    })
    r = client.post("/api/admin/login", json={"username": "admin", "password": "adminpass123"})
    assert r.status_code == 200
    token = r.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    r2 = client.get("/api/admin/overview", headers=headers)
    assert r2.status_code == 200
    data = r2.json()
    assert "total_users" in data
    assert data["total_users"] >= 1
