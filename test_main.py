from fastapi.testclient import TestClient
from app.main import app

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