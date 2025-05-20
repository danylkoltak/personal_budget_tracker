import pytest

@pytest.fixture
def user_data():
    return {
        "username": "testuser",
        "password": "testpass123"
    }

def test_register_user(client, user_data):
    response = client.post("/auth/", json=user_data)
    assert response.status_code == 201
    assert response.json()["message"] == "User created successfully"

def test_login_token(client, user_data):
    client.post("/auth/", json=user_data)
    response = client.post("/auth/token", data=user_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"