"""Focused regression tests for the 18 Finly bug fixes.

Covers BUG-01, BUG-02, BUG-04, BUG-07, BUG-08, BUG-14, BUG-15, BUG-17.
Frontend-only bugs (BUG-03, 05, 06, 09-13, 16, 18) are validated via
Playwright in the testing agent driver.
"""
from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


# ──────────────────────────── Fresh-user fixture ────────────────────────────
@pytest.fixture(scope="module")
def auth():
    """Fresh account per run avoids 409 conflicts and cross-test state."""
    email = f"bugfix_{uuid.uuid4().hex[:8]}@demo.co.id"
    password = "Password123"
    r = requests.post(
        f"{API}/auth/register",
        json={"email": email, "password": password, "name": "BugFix"},
        timeout=15,
    )
    assert r.status_code in (201, 409), r.text
    r = requests.post(
        f"{API}/auth/login",
        json={"email": email, "password": password},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    return {
        "token": data["token"],
        "user": data["user"],
        "email": email,
        "password": password,
        "headers": {"Authorization": f"Bearer {data['token']}"},
    }


# ──────────────────────────── BUG-14: CORS ────────────────────────────
def test_bug14_cors_headers_present():
    r = requests.options(
        f"{API}/",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
        timeout=10,
    )
    assert r.status_code in (200, 204), r.text
    assert "access-control-allow-origin" in {k.lower() for k in r.headers.keys()}


def test_bug14_cors_on_get():
    r = requests.get(f"{API}/", headers={"Origin": "https://example.com"}, timeout=10)
    assert r.status_code == 200
    assert "access-control-allow-origin" in {k.lower() for k in r.headers.keys()}


# ──────────────────────────── BUG-15 / BUG-17: startup log + indexes ────────────────────────────
def test_bug15_17_root_alive():
    """If lifespan crashed, / would 500. Index creation runs in lifespan."""
    r = requests.get(f"{API}/", timeout=10)
    assert r.status_code == 200
    assert r.json().get("message")


# ──────────────────────────── BUG-04: month validation ────────────────────────────
def test_bug04_invalid_month_returns_422(auth):
    r = requests.get(f"{API}/dashboard", params={"month": "2026-13"}, headers=auth["headers"], timeout=10)
    assert r.status_code == 422
    detail = r.json().get("detail", "")
    assert "Format bulan tidak valid" in detail, detail


def test_bug04_invalid_month_format(auth):
    r = requests.get(f"{API}/dashboard", params={"month": "bad-month"}, headers=auth["headers"], timeout=10)
    assert r.status_code == 422


def test_bug04_valid_month_ok(auth):
    r = requests.get(f"{API}/dashboard", params={"month": "2026-02"}, headers=auth["headers"], timeout=10)
    assert r.status_code == 200


# ──────────────────────────── BUG-01: total_expense + profit_loss ────────────────────────────
def test_bug01_total_expense_and_profit_loss(auth):
    month = "2026-03"
    # seed: 1 income (500000), 1 outcome (100000), a budget (200000), monthly_capital (50000)
    tx_in = requests.post(
        f"{API}/transactions",
        json={"type": "income", "category": "Gaji", "amount": 500000, "date": "2026-03-05", "description": "seed"},
        headers=auth["headers"], timeout=15,
    )
    assert tx_in.status_code in (200, 201), tx_in.text
    tx_out = requests.post(
        f"{API}/transactions",
        json={"type": "outcome", "category": "Makanan", "amount": 100000, "date": "2026-03-06", "description": "seed"},
        headers=auth["headers"], timeout=15,
    )
    assert tx_out.status_code in (200, 201), tx_out.text

    # Budget
    bg = requests.post(
        f"{API}/budgets",
        json={"month": month, "items": [{"category": "Makanan", "amount": 200000}]},
        headers=auth["headers"], timeout=15,
    )
    assert bg.status_code in (200, 201), bg.text

    # Monthly capital (separate endpoint)
    mc = requests.post(
        f"{API}/monthly-capital",
        json={"month": month, "amount": 50000, "description": "seed"},
        headers=auth["headers"], timeout=15,
    )
    assert mc.status_code in (200, 201), mc.text

    r = requests.get(f"{API}/dashboard", params={"month": month}, headers=auth["headers"], timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()

    assert "total_expense" in data, f"total_expense missing: {list(data.keys())}"
    assert "profit_loss" in data
    # formulas
    revenue = data["revenue"]
    outcome = data["outcome"]
    budget_total = data.get("budget_total", 0)
    monthly_capital = data.get("monthly_capital", 0)

    expected_total_expense = round(outcome + budget_total + monthly_capital, 2)
    expected_profit_loss = round(revenue - expected_total_expense, 2)

    assert data["total_expense"] == expected_total_expense, (data, expected_total_expense)
    assert data["profit_loss"] == expected_profit_loss, (data, expected_profit_loss)
    # Sanity: with 500000 income, 100000 outcome, 200000 budget, 50000 capital →
    # total_expense=350000, profit_loss=150000
    assert data["total_expense"] == 350000
    assert data["profit_loss"] == 150000


# ──────────────────────────── BUG-02: expired session purge ────────────────────────────
def test_bug02_invalid_token_returns_401():
    r = requests.get(f"{API}/dashboard", headers={"Authorization": "Bearer not-a-real-token"}, timeout=10)
    assert r.status_code == 401


def test_bug02_logout_invalidates_token(auth):
    # Use a separate login so we don't nuke the module-scoped fixture token.
    r = requests.post(
        f"{API}/auth/login",
        json={"email": auth["email"], "password": auth["password"]},
        timeout=15,
    )
    assert r.status_code == 200
    tok = r.json()["token"]
    headers = {"Authorization": f"Bearer {tok}"}
    # token valid
    assert requests.get(f"{API}/auth/me", headers=headers, timeout=10).status_code == 200
    # logout
    lo = requests.post(f"{API}/auth/logout", headers=headers, timeout=10)
    assert lo.status_code in (200, 204)
    # token now 401
    r2 = requests.get(f"{API}/auth/me", headers=headers, timeout=10)
    assert r2.status_code == 401


# ──────────────────────────── BUG-07: predict with no transactions ────────────────────────────
def test_bug07_predict_no_transactions_succeeds():
    # brand-new user → zero tx
    email = f"predict_{uuid.uuid4().hex[:8]}@demo.co.id"
    pw = "Password123"
    requests.post(f"{API}/auth/register", json={"email": email, "password": pw, "name": "P"}, timeout=15)
    login = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=15)
    tok = login.json()["token"]
    r = requests.post(
        f"{API}/predict",
        json={"n_days": 7},
        headers={"Authorization": f"Bearer {tok}"},
        timeout=90,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "forecast" in body or "predictions" in body or "data" in body, body
    # n_days respected
    assert body.get("n_days") == 7 or len(body.get("forecast", body.get("predictions", body.get("data", [])))) == 7


# ──────────────────────────── BUG-08: transactions limit=10000 allowed ────────────────────────────
def test_bug08_transactions_accepts_limit_10000(auth):
    r = requests.get(
        f"{API}/transactions",
        params={"limit": 10000, "page": 1},
        headers=auth["headers"],
        timeout=20,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    # structure check
    assert "data" in data or "transactions" in data or "items" in data, data
    # limit echo (if present) should be 10000
    if "limit" in data:
        assert data["limit"] == 10000


def test_bug08_transactions_limit_above_cap(auth):
    # 10001 should still 200 (clamped to 10000) – our max is 10000
    r = requests.get(
        f"{API}/transactions",
        params={"limit": 99999},
        headers=auth["headers"],
        timeout=20,
    )
    assert r.status_code == 200
    if "limit" in r.json():
        assert r.json()["limit"] == 10000
