"""Finly — Financial Analyst API (FastAPI + MongoDB).

Adapted from the PHP/MySQL/Flask spec to FastAPI + MongoDB while
preserving all 7 modules: Auth, Dashboard, Transactions, Budgets,
Predict (LSTM), Prediction History. All routes are prefixed with /api
and all data is strictly isolated per user.
"""
from __future__ import annotations

import logging
import os
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import List, Literal, Optional

import bcrypt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from starlette.middleware.cors import CORSMiddleware

from ml_forecast import ml_status, run_forecast

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("finly")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]


# ──────────────────────────── Lifespan (indexes + cleanup) ────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure useful indexes exist (BUG-17, BUG-02 TTL)
    try:
        await db.transactions.create_index([("user_id", 1), ("date", -1)])
        await db.transactions.create_index([("user_id", 1), ("type", 1), ("date", -1)])
        await db.budgets.create_index([("user_id", 1), ("month", 1)])
        await db.monthly_capital.create_index([("user_id", 1), ("month", 1)])
        await db.prediction_history.create_index([("user_id", 1), ("predicted_at", -1)])
        await db.sessions.create_index("token", unique=True)
        # TTL index on expires_at (expects a BSON date). Failing silently is fine
        # because expires_at is stored as ISO string here; we still proactively
        # delete stale rows in current_user().
        try:
            await db.sessions.create_index("expires_at_dt", expireAfterSeconds=0)
        except Exception:  # pragma: no cover
            pass
        logger.info("Mongo indexes ensured")
    except Exception as e:  # pragma: no cover
        logger.warning("Index creation skipped: %s", e)
    yield
    client.close()


app = FastAPI(title="Finly API", lifespan=lifespan)

# CORS must be registered before routers to keep middleware order sane (BUG-14)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")


# ──────────────────────────── Models ────────────────────────────
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: Optional[str] = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    name: Optional[str] = None


class TransactionIn(BaseModel):
    type: Literal["income", "outcome"]
    category: str = Field(min_length=1)
    amount: float = Field(gt=0)
    description: Optional[str] = ""
    date: date


class BudgetItem(BaseModel):
    category: str = Field(min_length=1)
    amount: float = Field(ge=0)


class BudgetSaveIn(BaseModel):
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    items: List[BudgetItem]


class PredictIn(BaseModel):
    n_days: int = Field(ge=1, le=90)


class MonthlyCapitalIn(BaseModel):
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    amount: float = Field(ge=0)
    description: Optional[str] = ""


# ──────────────────────────── Helpers ────────────────────────────
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


async def current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Unauthorized: Token tidak ditemukan")
    token = authorization.split(" ", 1)[1].strip()
    session = await db.sessions.find_one({"token": token}, {"_id": 0})
    if not session:
        raise HTTPException(401, "Unauthorized: Token tidak valid")
    expires = datetime.fromisoformat(session["expires_at"])
    if expires < datetime.now(timezone.utc):
        # BUG-02: purge stale tokens proactively
        await db.sessions.delete_one({"token": token})
        raise HTTPException(401, "Unauthorized: Token sudah kedaluwarsa")
    user = await db.users.find_one({"id": session["user_id"]}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(401, "Unauthorized: User tidak ditemukan")
    return user


def month_range(month_str: str) -> tuple[str, str]:
    # BUG-04: guard against malformed month strings
    try:
        parts = month_str.split("-")
        if len(parts) != 2:
            raise ValueError
        y, m = int(parts[0]), int(parts[1])
        if not (1 <= m <= 12) or y < 1970 or y > 3000:
            raise ValueError
    except (ValueError, AttributeError):
        raise HTTPException(422, f"Format bulan tidak valid: {month_str}")
    start = date(y, m, 1)
    end = date(y + (1 if m == 12 else 0), 1 if m == 12 else m + 1, 1)
    return start.isoformat(), end.isoformat()


# ──────────────────────────── Auth ────────────────────────────
@api.post("/auth/register", status_code=201)
async def register(body: RegisterIn):
    if await db.users.find_one({"email": body.email.lower()}):
        raise HTTPException(409, "Email sudah terdaftar")
    user = {
        "id": str(uuid.uuid4()),
        "email": body.email.lower(),
        "password": hash_password(body.password),
        "name": body.name or body.email.split("@")[0],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user)
    return {"success": True, "message": "Akun berhasil dibuat"}


@api.post("/auth/login")
async def login(body: LoginIn):
    user = await db.users.find_one({"email": body.email.lower()}, {"_id": 0})
    if not user or not verify_password(body.password, user["password"]):
        raise HTTPException(401, "Email atau password salah")
    token = secrets.token_hex(32)
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    await db.sessions.insert_one({
        "token": token,
        "user_id": user["id"],
        "expires_at": expires.isoformat(),
        "expires_at_dt": expires,  # BSON date for TTL index
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {
        "success": True,
        "token": token,
        "user": {"id": user["id"], "email": user["email"], "name": user.get("name")},
    }


@api.post("/auth/logout")
async def logout(user: dict = Depends(current_user), authorization: Optional[str] = Header(None)):
    if authorization:
        token = authorization.split(" ", 1)[1].strip()
        await db.sessions.delete_one({"token": token})
    return {"success": True}


@api.get("/auth/me", response_model=UserOut)
async def me(user: dict = Depends(current_user)):
    return {"id": user["id"], "email": user["email"], "name": user.get("name")}


# ──────────────────────────── Dashboard ────────────────────────────
@api.get("/dashboard")
async def dashboard(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    user: dict = Depends(current_user),
):
    start, end = month_range(month)
    txs = await db.transactions.find(
        {"user_id": user["id"], "date": {"$gte": start, "$lt": end}}, {"_id": 0}
    ).to_list(10000)

    revenue = round(sum(t["amount"] for t in txs if t["type"] == "income"), 2)
    outcome = round(sum(t["amount"] for t in txs if t["type"] == "outcome"), 2)

    budgets = await db.budgets.find(
        {"user_id": user["id"], "month": f"{month}-01"}, {"_id": 0}
    ).to_list(1000)
    budget_total = round(sum(b["amount"] for b in budgets), 2)

    capital_doc = await db.monthly_capital.find_one(
        {"user_id": user["id"], "month": f"{month}-01"}, {"_id": 0}
    )
    monthly_capital = round(float(capital_doc["amount"]), 2) if capital_doc else 0.0

    daily: dict[str, dict] = {}
    for t in txs:
        d = t["date"]
        if d not in daily:
            daily[d] = {"date": d, "income": 0.0, "outcome": 0.0}
        daily[d][t["type"]] += t["amount"]
    daily_chart = sorted(daily.values(), key=lambda x: x["date"])

    # Category breakdown for outcome
    cat_breakdown: dict[str, float] = {}
    for t in txs:
        if t["type"] == "outcome":
            cat_breakdown[t["category"]] = cat_breakdown.get(t["category"], 0.0) + t["amount"]
    category_chart = [
        {"category": k, "amount": round(v, 2)}
        for k, v in sorted(cat_breakdown.items(), key=lambda x: -x[1])
    ]

    # BUG-01: server is the single source of truth for P&L and expense totals
    total_expense = round(outcome + budget_total + monthly_capital, 2)
    profit_loss = round(revenue - total_expense, 2)

    return {
        "month": month,
        "revenue": revenue,
        "outcome": outcome,
        "budget_total": budget_total,
        "monthly_capital": monthly_capital,
        "total_expense": total_expense,
        "profit_loss": profit_loss,
        "transaction_count": len(txs),
        "daily_chart": daily_chart,
        "category_chart": category_chart,
    }


# ──────────────────────────── Transactions ────────────────────────────
@api.post("/transactions", status_code=201)
async def create_transaction(body: TransactionIn, user: dict = Depends(current_user)):
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "type": body.type,
        "category": body.category,
        "amount": float(body.amount),
        "description": body.description or "",
        "date": body.date.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.transactions.insert_one(doc)
    doc.pop("user_id", None)
    doc.pop("_id", None)
    return {"success": True, "id": doc["id"], "transaction": doc}


@api.get("/transactions")
async def list_transactions(
    month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    type: Optional[str] = "all",
    category: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    user: dict = Depends(current_user),
):
    q: dict = {"user_id": user["id"]}
    if month:
        start, end = month_range(month)
        q["date"] = {"$gte": start, "$lt": end}
    if type and type != "all":
        q["type"] = type
    if category and category not in (None, "", "all"):
        q["category"] = category
    if search:
        q["description"] = {"$regex": search, "$options": "i"}

    total = await db.transactions.count_documents(q)
    page = max(1, page)
    limit = max(1, min(10000, limit))
    cursor = (
        db.transactions.find(q, {"_id": 0, "user_id": 0})
        .sort("date", -1)
        .skip((page - 1) * limit)
        .limit(limit)
    )
    data = await cursor.to_list(limit)

    pipeline = [
        {"$match": q},
        {"$group": {"_id": "$type", "sum": {"$sum": "$amount"}}},
    ]
    agg = await db.transactions.aggregate(pipeline).to_list(10)
    totals = {"income": 0.0, "outcome": 0.0}
    for a in agg:
        totals[a["_id"]] = a["sum"]

    return {
        "data": data,
        "total": total,
        "page": page,
        "limit": limit,
        "totals": totals,
        "net": totals["income"] - totals["outcome"],
    }


@api.delete("/transactions/{tx_id}")
async def delete_transaction(tx_id: str, user: dict = Depends(current_user)):
    r = await db.transactions.delete_one({"id": tx_id, "user_id": user["id"]})
    if r.deleted_count == 0:
        raise HTTPException(404, "Transaksi tidak ditemukan")
    return {"success": True}


# ──────────────────────────── Budgets ────────────────────────────
@api.get("/budgets")
async def get_budgets(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    user: dict = Depends(current_user),
):
    budgets = await db.budgets.find(
        {"user_id": user["id"], "month": f"{month}-01"}, {"_id": 0, "user_id": 0}
    ).to_list(1000)

    start, end = month_range(month)
    pipeline = [
        {"$match": {"user_id": user["id"], "type": "outcome", "date": {"$gte": start, "$lt": end}}},
        {"$group": {"_id": "$category", "sum": {"$sum": "$amount"}}},
    ]
    agg = await db.transactions.aggregate(pipeline).to_list(1000)
    realisasi = {a["_id"]: a["sum"] for a in agg}

    items = []
    for b in budgets:
        cat = b["category"]
        real = realisasi.get(cat, 0.0)
        items.append({
            "id": b["id"],
            "category": cat,
            "budget": b["amount"],
            "realisasi": real,
            "selisih": b["amount"] - real,
            "status": "ok" if real <= b["amount"] else "over",
        })
    for cat, real in realisasi.items():
        if not any(i["category"] == cat for i in items):
            items.append({
                "id": None,
                "category": cat,
                "budget": 0.0,
                "realisasi": real,
                "selisih": -real,
                "status": "over",
            })

    capital_doc = await db.monthly_capital.find_one(
        {"user_id": user["id"], "month": f"{month}-01"}, {"_id": 0, "user_id": 0}
    )

    return {
        "month": month,
        "budgets": items,
        "total_budget": round(sum(b["amount"] for b in budgets), 2),
        "total_realisasi": round(sum(realisasi.values()), 2),
        "monthly_capital": capital_doc,
    }


@api.get("/monthly-capital")
async def get_monthly_capital(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    user: dict = Depends(current_user),
):
    doc = await db.monthly_capital.find_one(
        {"user_id": user["id"], "month": f"{month}-01"}, {"_id": 0, "user_id": 0}
    )
    return {"month": month, "capital": doc}


@api.post("/monthly-capital")
async def save_monthly_capital(body: MonthlyCapitalIn, user: dict = Depends(current_user)):
    month_key = f"{body.month}-01"
    await db.monthly_capital.update_one(
        {"user_id": user["id"], "month": month_key},
        {
            "$set": {
                "user_id": user["id"],
                "month": month_key,
                "amount": float(body.amount),
                "description": body.description or "",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            "$setOnInsert": {
                "id": str(uuid.uuid4()),
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        },
        upsert=True,
    )
    return {"success": True}


@api.delete("/monthly-capital")
async def delete_monthly_capital(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    user: dict = Depends(current_user),
):
    r = await db.monthly_capital.delete_one(
        {"user_id": user["id"], "month": f"{month}-01"}
    )
    if r.deleted_count == 0:
        raise HTTPException(404, "Modal awal tidak ditemukan")
    return {"success": True}


@api.post("/budgets")
async def save_budgets(body: BudgetSaveIn, user: dict = Depends(current_user)):
    month_key = f"{body.month}-01"
    for it in body.items:
        await db.budgets.update_one(
            {"user_id": user["id"], "month": month_key, "category": it.category},
            {
                "$set": {
                    "user_id": user["id"],
                    "month": month_key,
                    "category": it.category,
                    "amount": float(it.amount),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                "$setOnInsert": {
                    "id": str(uuid.uuid4()),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            },
            upsert=True,
        )
    return {"success": True}


@api.delete("/budgets/{budget_id}")
async def delete_budget(budget_id: str, user: dict = Depends(current_user)):
    r = await db.budgets.delete_one({"id": budget_id, "user_id": user["id"]})
    if r.deleted_count == 0:
        raise HTTPException(404, "Budget tidak ditemukan")
    return {"success": True}


# ──────────────────────────── ML Prediction ────────────────────────────
@api.post("/predict")
async def predict(body: PredictIn, user: dict = Depends(current_user)):
    n_days = body.n_days
    start = (date.today() - timedelta(days=90)).isoformat()
    txs = await db.transactions.find(
        {"user_id": user["id"], "type": "income", "date": {"$gte": start}},
        {"_id": 0, "date": 1, "amount": 1},
    ).to_list(10000)

    daily: dict[str, float] = {}
    for t in txs:
        daily[t["date"]] = daily.get(t["date"], 0.0) + float(t["amount"])
    user_daily = [{"tanggal": d, "nominal": v} for d, v in sorted(daily.items())]

    try:
        result = run_forecast(n_days=n_days, user_transactions=user_daily)
    except Exception as e:
        logger.exception("Forecast failed")
        raise HTTPException(503, f"ML Service error: {e}")

    predictions = result["predictions"]
    summary = result["ringkasan"]
    month_target = predictions[0]["tanggal"][:7] if predictions else datetime.now().strftime("%Y-%m")

    history_doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "predicted_at": datetime.now(timezone.utc).isoformat(),
        "n_days": n_days,
        "month_target": month_target,
        "total_predicted": summary["total"],
        "avg_daily": summary["rata_rata"],
        "min_daily": summary["minimum"],
        "max_daily": summary["maksimum"],
        "detail_json": predictions,
        "used_user_data": len(user_daily) > 0,
        "data_points": len(user_daily),
    }
    await db.prediction_history.insert_one(history_doc)

    return {
        "success": True,
        "id": history_doc["id"],
        "predictions": predictions,
        "summary": summary,
        "used_user_data": history_doc["used_user_data"],
        "data_points": history_doc["data_points"],
    }


@api.get("/prediction-history")
async def prediction_history(
    page: int = 1, limit: int = 10, user: dict = Depends(current_user)
):
    q = {"user_id": user["id"]}
    total = await db.prediction_history.count_documents(q)
    page = max(1, page)
    cursor = (
        db.prediction_history.find(q, {"_id": 0, "user_id": 0, "detail_json": 0})
        .sort("predicted_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
    )
    data = await cursor.to_list(limit)
    return {"data": data, "total": total, "page": page}


@api.get("/prediction-history/{pred_id}")
async def prediction_detail(pred_id: str, user: dict = Depends(current_user)):
    doc = await db.prediction_history.find_one(
        {"id": pred_id, "user_id": user["id"]}, {"_id": 0, "user_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Prediksi tidak ditemukan")
    return doc


@api.delete("/prediction-history/{pred_id}")
async def prediction_delete(pred_id: str, user: dict = Depends(current_user)):
    r = await db.prediction_history.delete_one({"id": pred_id, "user_id": user["id"]})
    if r.deleted_count == 0:
        raise HTTPException(404, "Prediksi tidak ditemukan")
    return {"success": True}


@api.get("/ml/health")
async def ml_health():
    return ml_status()


@api.get("/")
async def root():
    return {"message": "Finly API aktif", "version": "1.0"}


app.include_router(api)
