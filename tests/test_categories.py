import pytest

@pytest.fixture
def user_data():
    return {
        "username": "catuser",
        "password": "catpass123"
    }

@pytest.fixture
def auth_token(client, user_data):
    client.post("/auth/", json=user_data)
    response = client.post("/auth/token", data=user_data)
    return response.json()["access_token"]

def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}

def test_create_category(client, auth_token):
    payload = {"category_name": "Groceries"}
    response = client.post("/categories/", json=payload, headers=auth_headers(auth_token))
    assert response.status_code == 201
    assert "id" in response.json()
    assert "Category 'Groceries' created successfully" in response.json()["message"]

def test_create_duplicate_category(client, auth_token):
    payload = {"category_name": "Utilities"}
    client.post("/categories/", json=payload, headers=auth_headers(auth_token))
    response = client.post("/categories/", json=payload, headers=auth_headers(auth_token))
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

def test_get_all_categories(client, auth_token):
    client.post("/categories/", json={"category_name": "Transport"}, headers=auth_headers(auth_token))
    response = client.get("/categories/", headers=auth_headers(auth_token))
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert any(cat["category_name"] == "Transport" for cat in response.json())

def test_edit_category(client, auth_token):
    create_resp = client.post("/categories/", json={"category_name": "OldName"}, headers=auth_headers(auth_token))
    cat_id = create_resp.json()["id"]
    response = client.put(f"/categories/{cat_id}", json={"category_name": "NewName"}, headers=auth_headers(auth_token))
    assert response.status_code == 200
    data = response.json()
    assert data["category_id"] == cat_id
    assert data["category_name"] == "NewName"

def test_delete_category(client, auth_token):
    create_resp = client.post("/categories/", json={"category_name": "ToDelete"}, headers=auth_headers(auth_token))
    cat_id = create_resp.json()["id"]
    response = client.delete(f"/categories/{cat_id}", headers=auth_headers(auth_token))
    assert response.status_code == 204