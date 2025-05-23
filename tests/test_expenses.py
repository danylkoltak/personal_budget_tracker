import pytest
import uuid

@pytest.fixture
def user_data():
    return {
        "username": "expenseuser",
        "password": "expensepass123"
    }

@pytest.fixture
def auth_token(client, user_data):
    client.post("/auth/", json=user_data)
    response = client.post("/auth/token", data=user_data)
    return response.json()["access_token"]

def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def category_id(client, auth_token):
    unique_name = f"Food-{uuid.uuid4()}"
    payload = {"category_name": unique_name}
    response = client.post("/categories/", json=payload, headers=auth_headers(auth_token))
    print("Category response:", response.status_code, response.json())
    return response.json()["id"]

def test_create_expense(client, auth_token, category_id):
    payload = {
        "added_expense_amount": 25.5,
        "expense_description": "Lunch",
        "category_id": category_id
    }
    response = client.post("/expenses/", json=payload, headers=auth_headers(auth_token))
    if response.status_code != 201:
        print("Expense response:", response.status_code, response.json())
    assert response.status_code == 201
    data = response.json()
    assert data["added_expense_amount"] == 25.5
    assert data["expense_description"] == "Lunch"
    assert data["category_id"] == category_id

def test_get_expenses(client, auth_token, category_id):
    client.post("/expenses/", json={
        "added_expense_amount": 10,
        "expense_description": "Coffee",
        "category_id": category_id
    }, headers=auth_headers(auth_token))
    response = client.get(f"/expenses/{category_id}", headers=auth_headers(auth_token))
    assert response.status_code == 200
    expenses = response.json()
    assert isinstance(expenses, list)
    assert any(exp["expense_description"] == "Coffee" for exp in expenses)

def test_update_expense(client, auth_token, category_id):
    create_resp = client.post("/expenses/", json={
        "added_expense_amount": 5,
        "expense_description": "Snack",
        "category_id": category_id
    }, headers=auth_headers(auth_token))
    expense_id = create_resp.json()["expense_id"]
    update_payload = {
        "added_expense_amount": 7,
        "expense_description": "Snack (updated)",
        "category_id": category_id
    }
    response = client.put(f"/expenses/{expense_id}", json=update_payload, headers=auth_headers(auth_token))
    assert response.status_code == 200
    data = response.json()
    assert data["expense_id"] == expense_id
    assert data["added_expense_amount"] == 7
    assert data["expense_description"] == "Snack (updated)"
    assert data["category_id"] == category_id


def test_delete_expense(client, auth_token, category_id):
    create_resp = client.post("/expenses/", json={
        "added_expense_amount": 3,
        "expense_description": "Water",
        "category_id": category_id
    }, headers=auth_headers(auth_token))
    expense_id = create_resp.json()["expense_id"]
    response = client.delete(f"/expenses/{expense_id}", headers=auth_headers(auth_token))
    assert response.status_code == 204