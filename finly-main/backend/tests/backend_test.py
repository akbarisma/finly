"""Finly backend regression tests.

Covers: auth (register/login/logout/me), dashboard, transactions
(CRUD+filter+pagination+isolation), budgets (upsert+realisasi),
ML predict + prediction-history, ml/health.
"""
from __future__ import annotations

import os
import time
import uuid
from datetime import date, datetime, timedelta

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get(
    "REACT_APP_BACKEND_URL"
) else "https://ui-cleanup-app.preview.emergentagent.com"
API = f"{BASE_URL}/api"

# Shared demo accounts
DEMO_EMAIL = "demo@finly.id"
DEMO_EMAIL_2 = "demo2@finly.id"
DEMO_PASS = "demo12345"

# Current month matches server date reference (April 2026 per spec)
def current_month() -> str:
    return datetime.now().strftime("%Y-%m")


# ──────────────────────────── Fixtures ────────────────────────────
@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _ensure_user(session, email: str, password: str, name: str = "Test"):
    """Register (ignore 409) + return token."""
    session.post(f"{API}/auth/register", json={"email": email, "password": password, "name": name}, timeout=15)
    r = session.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"Login failed for {email}: {r.text}"
    return r.json()["token"], r.json()["user"]


@pytest.fixture(scope="session")
def demo_auth(session):
    token, user = _ensure_user(session, DEMO_EMAIL, DEMO_PASS, "Demo")
    return {"token": token, "user": user, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture(scope="session")
def demo2_auth(session):
    token, user = _ensure_user(session, DEMO_EMAIL_2, DEMO_PASS, "Demo Dua")
    return {"token": token, "user": user, "headers": {"Authorization": f"Bearer {token}"}}


# ──────────────────────────── Health ────────────────────────────
class TestHealth:
    def test_api_root(self, session):
        r = session.get(f"{API}/", timeout=10)
        assert r.status_code == 200
        assert "Finly" in r.json().get("message", "")

    def test_ml_health(self, session):
        r = session.get(f"{API}/ml/health", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "input_shape" in data
        # LSTM expected: (None, 14, 39)
        assert data["input_shape"][1:] == [14, 39]


# ──────────────────────────── Auth ────────────────────────────
class TestAuth:
    def test_register_validation_short_password(self, session):
        r = session.post(f"{API}/auth/register", json={
            "email": f"TEST_short_{uuid.uuid4().hex[:6]}@finly.id",
            "password": "short",
            "name": "T"
        }, timeout=10)
        assert r.status_code == 422

    def test_register_validation_invalid_email(self, session):
        r = session.post(f"{API}/auth/register", json={
            "email": "not-an-email", "password": "12345678"
        }, timeout=10)
        assert r.status_code == 422

    def test_register_success_and_duplicate(self, session):
        email = f"TEST_dup_{uuid.uuid4().hex[:6]}@finly.id"
        r1 = session.post(f"{API}/auth/register", json={
            "email": email, "password": "password123", "name": "Dup"
        }, timeout=10)
        assert r1.status_code == 201
        assert r1.json().get("success") is True

        r2 = session.post(f"{API}/auth/register", json={
            "email": email, "password": "password123"
        }, timeout=10)
        assert r2.status_code == 409

    def test_login_success(self, demo_auth):
        assert demo_auth["token"]
        assert demo_auth["user"]["email"] == DEMO_EMAIL

    def test_login_wrong_password(self, session):
        r = session.post(f"{API}/auth/login", json={
            "email": DEMO_EMAIL, "password": "wrongpassword"
        }, timeout=10)
        assert r.status_code == 401

    def test_login_nonexistent(self, session):
        r = session.post(f"{API}/auth/login", json={
            "email": "TEST_none_xyz@finly.id", "password": "password123"
        }, timeout=10)
        assert r.status_code == 401

    def test_me_with_valid_token(self, session, demo_auth):
        r = session.get(f"{API}/auth/me", headers=demo_auth["headers"], timeout=10)
        assert r.status_code == 200
        assert r.json()["email"] == DEMO_EMAIL

    def test_me_without_token(self, session):
        r = session.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 401

    def test_me_invalid_token(self, session):
        r = session.get(f"{API}/auth/me", headers={"Authorization": "Bearer invalidxxxx"}, timeout=10)
        assert r.status_code == 401

    def test_logout_invalidates_token(self, session):
        # Separate user so we don't kill demo session
        email = f"TEST_logout_{uuid.uuid4().hex[:6]}@finly.id"
        session.post(f"{API}/auth/register", json={"email": email, "password": "password123"}, timeout=10)
        r = session.post(f"{API}/auth/login", json={"email": email, "password": "password123"}, timeout=10)
        token = r.json()["token"]
        h = {"Authorization": f"Bearer {token}"}
        assert session.get(f"{API}/auth/me", headers=h, timeout=10).status_code == 200
        assert session.post(f"{API}/auth/logout", headers=h, timeout=10).status_code == 200
        assert session.get(f"{API}/auth/me", headers=h, timeout=10).status_code == 401


# ──────────────────────────── Transactions ────────────────────────────
class TestTransactions:
    def test_create_income_and_verify(self, session, demo_auth):
        today = date.today().isoformat()
        payload = {"type": "income", "category": "Penjualan",
                   "amount": 1500000, "description": "TEST_tx_income", "date": today}
        r = session.post(f"{API}/transactions", headers=demo_auth["headers"], json=payload, timeout=10)
        assert r.status_code == 201, r.text
        tx = r.json()["transaction"]
        assert tx["type"] == "income"
        assert tx["amount"] == 1500000
        assert tx["category"] == "Penjualan"
        assert "id" in tx and "user_id" not in tx

        # GET to verify persistence
        mth = current_month()
        lr = session.get(f"{API}/transactions?month={mth}&search=TEST_tx_income",
                         headers=demo_auth["headers"], timeout=10)
        assert lr.status_code == 200
        ids = [t["id"] for t in lr.json()["data"]]
        assert tx["id"] in ids

    def test_create_validation_negative_amount(self, session, demo_auth):
        r = session.post(f"{API}/transactions", headers=demo_auth["headers"], json={
            "type": "income", "category": "Penjualan", "amount": -5, "date": date.today().isoformat()
        }, timeout=10)
        assert r.status_code == 422

    def test_create_validation_invalid_type(self, session, demo_auth):
        r = session.post(f"{API}/transactions", headers=demo_auth["headers"], json={
            "type": "badtype", "category": "Penjualan", "amount": 1000, "date": date.today().isoformat()
        }, timeout=10)
        assert r.status_code == 422

    def test_filter_by_type_and_pagination(self, session, demo_auth):
        mth = current_month()
        # Ensure multiple outcomes exist
        for i in range(3):
            session.post(f"{API}/transactions", headers=demo_auth["headers"], json={
                "type": "outcome", "category": "Operasional",
                "amount": 10000 + i, "description": f"TEST_tx_out_{i}",
                "date": date.today().isoformat()
            }, timeout=10)
        r = session.get(f"{API}/transactions?month={mth}&type=outcome&limit=2&page=1",
                        headers=demo_auth["headers"], timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert body["limit"] == 2
        assert len(body["data"]) <= 2
        for t in body["data"]:
            assert t["type"] == "outcome"

    def test_delete_transaction(self, session, demo_auth):
        r = session.post(f"{API}/transactions", headers=demo_auth["headers"], json={
            "type": "income", "category": "Penjualan", "amount": 111,
            "description": "TEST_to_delete", "date": date.today().isoformat()
        }, timeout=10)
        tx_id = r.json()["transaction"]["id"]
        d = session.delete(f"{API}/transactions/{tx_id}", headers=demo_auth["headers"], timeout=10)
        assert d.status_code == 200
        # deleting again -> 404
        d2 = session.delete(f"{API}/transactions/{tx_id}", headers=demo_auth["headers"], timeout=10)
        assert d2.status_code == 404

    def test_user_isolation(self, session, demo_auth, demo2_auth):
        # create under demo2
        r = session.post(f"{API}/transactions", headers=demo2_auth["headers"], json={
            "type": "income", "category": "Penjualan", "amount": 999,
            "description": "TEST_isolation", "date": date.today().isoformat()
        }, timeout=10)
        tx_id = r.json()["transaction"]["id"]
        # demo tries to delete -> 404
        d = session.delete(f"{API}/transactions/{tx_id}", headers=demo_auth["headers"], timeout=10)
        assert d.status_code == 404
        # demo list should not contain tx_id
        mth = current_month()
        listing = session.get(f"{API}/transactions?month={mth}&search=TEST_isolation",
                              headers=demo_auth["headers"], timeout=10).json()
        assert all(t["id"] != tx_id for t in listing["data"])


# ──────────────────────────── Dashboard ────────────────────────────
class TestDashboard:
    def test_dashboard_shape(self, session, demo_auth):
        mth = current_month()
        r = session.get(f"{API}/dashboard?month={mth}", headers=demo_auth["headers"], timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ["month", "revenue", "outcome", "budget_total", "profit_loss",
                  "transaction_count", "daily_chart", "category_chart"]:
            assert k in d
        assert d["month"] == mth
        assert isinstance(d["daily_chart"], list)
        assert isinstance(d["category_chart"], list)

    def test_dashboard_invalid_month_format(self, session, demo_auth):
        r = session.get(f"{API}/dashboard?month=2026/04", headers=demo_auth["headers"], timeout=10)
        assert r.status_code == 422


# ──────────────────────────── Budgets ────────────────────────────
class TestBudgets:
    def test_save_and_get_budgets_upsert(self, session, demo_auth):
        mth = current_month()
        payload = {"month": mth, "items": [
            {"category": "Operasional", "amount": 500000},
            {"category": "Marketing", "amount": 300000},
        ]}
        r = session.post(f"{API}/budgets", headers=demo_auth["headers"], json=payload, timeout=10)
        assert r.status_code == 200
        assert r.json()["success"] is True

        # Upsert - change amount
        r2 = session.post(f"{API}/budgets", headers=demo_auth["headers"], json={
            "month": mth, "items": [{"category": "Operasional", "amount": 700000}]
        }, timeout=10)
        assert r2.status_code == 200

        g = session.get(f"{API}/budgets?month={mth}", headers=demo_auth["headers"], timeout=10)
        assert g.status_code == 200
        data = g.json()
        cats = {b["category"]: b for b in data["budgets"]}
        assert cats["Operasional"]["budget"] == 700000
        assert cats["Marketing"]["budget"] == 300000
        # realisasi/status present
        for b in data["budgets"]:
            assert "realisasi" in b
            assert b["status"] in ("ok", "over")

    def test_budget_realisasi_from_outcome(self, session, demo_auth):
        mth = current_month()
        # set small budget to force 'over'
        session.post(f"{API}/budgets", headers=demo_auth["headers"], json={
            "month": mth, "items": [{"category": "TEST_BUDCAT", "amount": 100}]
        }, timeout=10)
        # create outcome in that category
        session.post(f"{API}/transactions", headers=demo_auth["headers"], json={
            "type": "outcome", "category": "TEST_BUDCAT", "amount": 5000,
            "description": "TEST_bud_real", "date": date.today().isoformat()
        }, timeout=10)
        g = session.get(f"{API}/budgets?month={mth}", headers=demo_auth["headers"], timeout=10).json()
        row = next((b for b in g["budgets"] if b["category"] == "TEST_BUDCAT"), None)
        assert row is not None
        assert row["realisasi"] >= 5000
        assert row["status"] == "over"


# ──────────────────────────── ML Prediction ────────────────────────────
class TestPredict:
    @pytest.fixture(scope="class")
    def prediction_result(self, session):
        # Use demo account
        r = session.post(f"{API}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASS}, timeout=15)
        token = r.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        # Warm-up + run
        res = session.post(f"{API}/predict", headers=headers, json={"n_days": 7}, timeout=120)
        return headers, res

    def test_predict_7_days(self, prediction_result):
        _, res = prediction_result
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["success"] is True
        assert "id" in body
        assert len(body["predictions"]) == 7
        for p in body["predictions"]:
            assert "tanggal" in p and "hari" in p and "prediksi" in p
            assert p["prediksi"] >= 0
        s = body["summary"]
        for k in ["total", "rata_rata", "minimum", "maksimum"]:
            assert k in s

    def test_predict_bounds_invalid(self, session, demo_auth):
        r = session.post(f"{API}/predict", headers=demo_auth["headers"], json={"n_days": 0}, timeout=15)
        assert r.status_code == 422
        r2 = session.post(f"{API}/predict", headers=demo_auth["headers"], json={"n_days": 91}, timeout=15)
        assert r2.status_code == 422

    def test_predict_requires_auth(self, session):
        r = session.post(f"{API}/predict", json={"n_days": 7}, timeout=15)
        assert r.status_code == 401


# ──────────────────────────── Prediction History ────────────────────────────
class TestPredictionHistory:
    def test_history_list_and_detail_and_delete(self, session, demo_auth):
        # Ensure at least one prediction exists
        pr = session.post(f"{API}/predict", headers=demo_auth["headers"], json={"n_days": 3}, timeout=120)
        assert pr.status_code == 200
        pred_id = pr.json()["id"]

        lst = session.get(f"{API}/prediction-history?page=1&limit=10",
                          headers=demo_auth["headers"], timeout=15)
        assert lst.status_code == 200
        body = lst.json()
        assert body["total"] >= 1
        assert any(x["id"] == pred_id for x in body["data"])
        # List excludes detail_json (lightweight)
        assert all("detail_json" not in x for x in body["data"])

        det = session.get(f"{API}/prediction-history/{pred_id}",
                          headers=demo_auth["headers"], timeout=15)
        assert det.status_code == 200
        d = det.json()
        assert d["id"] == pred_id
        assert isinstance(d.get("detail_json"), list)
        assert len(d["detail_json"]) == 3

        dl = session.delete(f"{API}/prediction-history/{pred_id}",
                            headers=demo_auth["headers"], timeout=15)
        assert dl.status_code == 200

        det2 = session.get(f"{API}/prediction-history/{pred_id}",
                           headers=demo_auth["headers"], timeout=15)
        assert det2.status_code == 404

    def test_history_isolation(self, session, demo_auth, demo2_auth):
        r = session.post(f"{API}/predict", headers=demo2_auth["headers"],
                         json={"n_days": 2}, timeout=120)
        assert r.status_code == 200
        pred_id = r.json()["id"]
        # demo tries to view -> 404
        r2 = session.get(f"{API}/prediction-history/{pred_id}",
                         headers=demo_auth["headers"], timeout=15)
        assert r2.status_code == 404
        # demo delete -> 404
        r3 = session.delete(f"{API}/prediction-history/{pred_id}",
                            headers=demo_auth["headers"], timeout=15)
        assert r3.status_code == 404
