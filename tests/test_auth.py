import pytest

test_username = "testuser"
test_password = "testpass123"

def test_register_user(client):
    response = client.post("/auth/", json={
        "username": test_username,
        "password": test_password
    })
    assert response.status_code == 201
    assert response.json()["message"] == "User created successfully"

def test_login_token(client):
    response = client.post("/auth/token", data={
        "username": test_username,
        "password": test_password
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"