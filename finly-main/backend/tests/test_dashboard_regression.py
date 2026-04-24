"""Regression tests for dashboard KPI formula and money-group CRUD flows (iter 4)."""
import os
import uuid
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://ui-cleanup-app.preview.emergentagent.com").rstrip("/")


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    email = f"TEST_iter4_{uuid.uuid4().hex[:8]}@demo.co.id"
    pw = "Password123"
    r = s.post(f"{BASE}/api/auth/register", json={"email": email, "password": pw, "name": "iter4"})
    assert r.status_code in (201, 200), r.text
    r = s.post(f"{BASE}/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200
    token = r.json()["token"]
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


# BE regression: dashboard total_expense = outcome + budget_total + monthly_capital
def test_dashboard_formula_full(client):
    month = "2026-01"
    # income 2M
    client.post(f"{BASE}/api/transactions", json={
        "type": "income", "category": "Penjualan", "amount": 2000000,
        "description": "TEST revenue", "date": f"{month}-05"})
    # outcome 300k
    client.post(f"{BASE}/api/transactions", json={
        "type": "outcome", "category": "Operasional", "amount": 300000,
        "description": "TEST outcome", "date": f"{month}-06"})
    # budget total 700k
    r = client.post(f"{BASE}/api/budgets", json={
        "month": month, "items": [{"category": "Operasional", "amount": 700000}]})
    assert r.status_code == 200
    # monthly_capital 500k
    r = client.post(f"{BASE}/api/monthly-capital", json={
        "month": month, "amount": 500000, "description": "TEST capital"})
    assert r.status_code == 200

    r = client.get(f"{BASE}/api/dashboard?month={month}")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["revenue"] == 2000000
    assert d["outcome"] == 300000
    assert d["budget_total"] == 700000
    assert d["monthly_capital"] == 500000
    # 300k + 700k + 500k = 1.5M
    assert d["total_expense"] == 1500000, d
    # 2M - 1.5M = 500k
    assert d["profit_loss"] == 500000, d


def test_monthly_capital_crud(client):
    month = "2026-02"
    r = client.post(f"{BASE}/api/monthly-capital", json={
        "month": month, "amount": 250000, "description": "TEST cap2"})
    assert r.status_code == 200
    r = client.get(f"{BASE}/api/budgets?month={month}")
    assert r.status_code == 200
    cap = r.json()["monthly_capital"]
    assert cap and cap["amount"] == 250000
    r = client.delete(f"{BASE}/api/monthly-capital?month={month}")
    assert r.status_code == 200
    r = client.get(f"{BASE}/api/budgets?month={month}")
    assert r.json()["monthly_capital"] is None


def test_transaction_crud(client):
    r = client.post(f"{BASE}/api/transactions", json={
        "type": "outcome", "category": "Marketing", "amount": 50000,
        "description": "TEST", "date": "2026-01-15"})
    assert r.status_code == 201
    tid = r.json()["id"]
    r = client.delete(f"{BASE}/api/transactions/{tid}")
    assert r.status_code == 200
