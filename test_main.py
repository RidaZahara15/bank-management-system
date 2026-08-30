import os
os.environ["TESTING"] = "true"
from fastapi.testclient import TestClient
from app.main import app
import uuid


client = TestClient(app)


# ===== Basic Endpoints =====

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200


# ===== Signup Tests =====

def test_signup_missing_fields():
    response = client.post("/users", json={"name": "Test"})
    assert response.status_code == 422


def test_signup_invalid_email():
    response = client.post("/users", json={
        "name": "Test User",
        "email": "not-an-email",
        "password": "test123"
    })
    assert response.status_code == 422


# ===== Login Tests =====

def test_login_missing_password():
    response = client.post("/login", json={"email": "test@example.com"})
    assert response.status_code == 422


def test_login_wrong_credentials():
    response = client.post("/login", json={
        "email": "nonexistent@example.com",
        "password": "wrongpassword",
        "captcha_token": "dummy"
    })
    assert response.status_code in [401, 400]


# ===== Protected Endpoints (without token ) =====

def test_accounts_without_token():
    response = client.get("/accounts")
    assert response.status_code in [401, 403]


def test_profile_without_token():
    response = client.get("/profile")
    assert response.status_code in [401, 403]


def test_deposit_without_token():
    response = client.post("/accounts/1/deposit", json={"amount": 100})
    assert response.status_code in [401, 403]


def test_transfer_without_token():
    response = client.post("/transfer", json={
        "from_account_id": 1,
        "to_account_id": 2,
        "amount": 100
    })
    assert response.status_code in [401, 403]

# ===== Success Endpoints=====


def test_signup_success():
    unique_email = f"pytest_{uuid.uuid4()}@example.com"
    response = client.post("/users", json={
        "name": "Pytest User",
        "email": unique_email,
        "password": "testpass123"
    })
    assert response.status_code == 200
    assert response.json()["email"] == unique_email


def test_login_success():
    unique_email = f"logintest_{uuid.uuid4()}@example.com"
    client.post("/users", json={
        "name": "Login Test",
        "email": unique_email,
        "password": "test123"
    })
    response = client.post("/login", json={
        "email": unique_email,
        "password": "test123",
        "captcha_token": "dummy"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_full_banking_flow():
    unique_email = f"flowtest_{uuid.uuid4()}@example.com"
    client.post("/users", json={
        "name": "Flow Test",
        "email": unique_email,
        "password": "test123"
    })
    login_response = client.post("/login", json={
        "email": unique_email,
        "password": "test123",
        "captcha_token": "dummy"
    })
    token = login_response.json()["access_token"]
    headers = {"Authorization": "Bearer " + token}

    account_response = client.post("/accounts", json={"account_type": "savings"}, headers=headers)
    assert account_response.status_code == 200
    account_id = account_response.json()["id"]

    deposit_response = client.post(f"/accounts/{account_id}/deposit", json={"amount": 500}, headers=headers)
    assert deposit_response.status_code == 200
    assert deposit_response.json()["amount"] == 500

    withdraw_response = client.post(f"/accounts/{account_id}/withdraw", json={"amount": 100}, headers=headers)
    assert withdraw_response.status_code == 200