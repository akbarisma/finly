"""LSTM forecast helper for Finly.

Loads the pre-trained LSTM model + MinMaxScaler and produces daily
forecasts given the user's historical daily income.

The original model was trained on restaurant sales data with 27 base
features (calendar + target). At inference time we build a 27-column
dataframe from user transactions (filling calendar fields) then expand
to 39 features via temporal engineering (lags, rolling, momentum) —
this mirrors the structure expected by the saved Keras model
(input_shape = 14 × 39).
"""
from __future__ import annotations

import logging
import os
import warnings
from datetime import datetime, timedelta
from pathlib import Path

warnings.filterwarnings("ignore")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

logger = logging.getLogger("finly.ml")

MODEL_DIR = Path(__file__).parent / "ml_models"
MODEL_PATH = MODEL_DIR / "LSTM_model.keras"
SCALER_PATH = MODEL_DIR / "lstm_scaler.pkl"
TARGET_COLUMN = "2to5"
TIME_STEPS = 14

BASE_FEATURES = [
    "Year", "Day",
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
    "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
    "Holiday", "Carnival", "LentFasting", "Ramadan", "ChristmasSeason",
    TARGET_COLUMN,
]

_MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
_WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

_model = None
_scaler = None
_load_error: str | None = None


def _load():
    global _model, _scaler, _load_error
    if _model is not None and _scaler is not None:
        return
    try:
        import joblib
        from tensorflow.keras.models import load_model  # type: ignore

        logger.info("Loading LSTM model from %s", MODEL_PATH)
        _model = load_model(str(MODEL_PATH), compile=False)
        _scaler = joblib.load(str(SCALER_PATH))
        logger.info("LSTM model loaded (input %s)", _model.input_shape)
    except Exception as e:  # pragma: no cover - environment dependent
        _load_error = str(e)
        logger.exception("LSTM load failed: %s", e)


def ml_status() -> dict:
    _load()
    if _model is not None:
        return {
            "status": "ok",
            "model_path": str(MODEL_PATH),
            "input_shape": list(_model.input_shape),
            "n_features_base": _scaler.n_features_in_,
        }
    return {"status": "error", "message": _load_error or "model not loaded"}


# ──────────────────────────── Feature builder ────────────────────────────
def _calendar_row(d: datetime, target_val: float) -> dict:
    row = {k: 0 for k in BASE_FEATURES}
    row["Year"] = d.year
    row["Day"] = d.day
    row[_MONTH_NAMES[d.month - 1]] = 1
    row[_WEEKDAY_NAMES[d.weekday()]] = 1
    row[TARGET_COLUMN] = float(target_val)
    return row


def _build_history_df(user_tx: list[dict]) -> pd.DataFrame:
    """Create a daily DataFrame with all BASE_FEATURES columns.

    Guarantees at least `TIME_STEPS + 35` rows by back-filling zeros if
    the user has fewer historical days, so the temporal feature window
    can be computed without NaNs.
    """
    if user_tx:
        # dict: tanggal -> nominal (already aggregated upstream but be safe)
        daily = {}
        for t in user_tx:
            daily[t["tanggal"]] = daily.get(t["tanggal"], 0.0) + float(t["nominal"])
        last_date = max(pd.to_datetime(d) for d in daily.keys())
        avg_val = float(np.mean(list(daily.values())))
    else:
        daily = {}
        last_date = pd.Timestamp(datetime.now().date())
        avg_val = 0.0

    # Need at least TIME_STEPS + max rolling window (30) + few spare = 50
    min_rows = TIME_STEPS + 40
    start_date = last_date - pd.Timedelta(days=min_rows - 1)

    rows = []
    cur = start_date
    while cur <= last_date:
        key = cur.strftime("%Y-%m-%d")
        val = daily.get(key, avg_val if daily else 0.0)
        rows.append(_calendar_row(cur.to_pydatetime(), val))
        cur += pd.Timedelta(days=1)

    df = pd.DataFrame(rows, columns=BASE_FEATURES, index=pd.DatetimeIndex(
        pd.date_range(start=start_date, end=last_date, freq="D")
    ))
    return df


def _add_temporal(df_scaled: pd.DataFrame) -> pd.DataFrame:
    out = df_scaled.copy()
    for lag in [1, 2, 3, 7, 14]:
        out[f"lag_{lag}"] = out[TARGET_COLUMN].shift(lag)
    for window in [7, 14, 30]:
        out[f"rolling_mean_{window}"] = out[TARGET_COLUMN].shift(1).rolling(window).mean()
        out[f"rolling_std_{window}"] = out[TARGET_COLUMN].shift(1).rolling(window).std()
    out["momentum_1"] = out[TARGET_COLUMN].diff(1)
    out["momentum_7"] = out[TARGET_COLUMN].diff(7)
    return out.dropna()


def _inverse_target(scaled_val: float) -> float:
    target_idx = list(_scaler.feature_names_in_).index(TARGET_COLUMN)
    n = _scaler.n_features_in_
    dummy = np.zeros((1, n))
    dummy[0, target_idx] = scaled_val
    return float(_scaler.inverse_transform(dummy)[0, target_idx])


# ──────────────────────────── Main forecast ────────────────────────────
def run_forecast(n_days: int, user_transactions: list[dict] | None = None) -> dict:
    _load()
    n_days = max(1, min(90, int(n_days)))
    user_transactions = user_transactions or []

    if _model is None or _scaler is None:
        # Fallback: moving-average style forecast so the app stays usable
        return _fallback_forecast(n_days, user_transactions)

    df_hist = _build_history_df(user_transactions)
    # Ensure columns in scaler order
    feature_order = list(_scaler.feature_names_in_)
    df_hist = df_hist[feature_order]

    scaled = _scaler.transform(df_hist.values)
    df_scaled = pd.DataFrame(scaled, columns=feature_order, index=df_hist.index)
    df_feat = _add_temporal(df_scaled)
    # Drop target column from input features (model was trained on X only)
    df_feat_x = df_feat.drop(columns=[TARGET_COLUMN])

    all_cols = df_feat_x.columns.tolist()
    target_history = list(df_feat[TARGET_COLUMN].values[-max(TIME_STEPS, 30) - 5:])
    if len(df_feat_x) < TIME_STEPS:
        return _fallback_forecast(n_days, user_transactions)

    window = df_feat_x.values[-TIME_STEPS:].copy()
    history = target_history
    # BUG-07: ensure history is long enough so lag_14 / rolling_30 never
    # read out-of-bound indexes (pad left with the earliest known value).
    min_hist = 35
    if len(history) < min_hist:
        pad_val = history[0] if history else 0.0
        history = [pad_val] * (min_hist - len(history)) + history
    last_date = df_feat_x.index[-1]

    col_map = {c: i for i, c in enumerate(all_cols)}
    predictions = []

    for day in range(n_days):
        inp = window.reshape(1, TIME_STEPS, len(all_cols))
        pred_sc = float(_model.predict(inp, verbose=0)[0][0])
        pred_val = _inverse_target(pred_sc)
        future = last_date + pd.Timedelta(days=day + 1)
        predictions.append({
            "tanggal": future.strftime("%Y-%m-%d"),
            "hari": future.strftime("%A"),
            "prediksi": round(max(0.0, pred_val), 2),
        })

        # Build next row with fresh calendar fields for the future date
        new_row = window[-1].copy()
        fut_py = future.to_pydatetime()
        cal = _calendar_row(fut_py, pred_val)
        cal_scaled = _scaler.transform(
            pd.DataFrame([cal], columns=feature_order).values
        )[0]
        # Fill in calendar columns (skip TARGET_COLUMN since it's not in input)
        for idx, col in enumerate(feature_order):
            if col == TARGET_COLUMN:
                continue
            if col in col_map:
                new_row[col_map[col]] = cal_scaled[idx]
        history.append(pred_sc)

        # Update temporal features
        n = len(history) - 1

        def gv(i: int) -> float:
            return history[i] if 0 <= i < len(history) else 0.0

        for lag in [1, 2, 3, 7, 14]:
            if f"lag_{lag}" in col_map:
                new_row[col_map[f"lag_{lag}"]] = gv(n - lag + 1)
        for w in [7, 14, 30]:
            vals = [gv(n - w + 1 + i) for i in range(w)]
            if f"rolling_mean_{w}" in col_map:
                new_row[col_map[f"rolling_mean_{w}"]] = float(np.mean(vals))
            if f"rolling_std_{w}" in col_map:
                new_row[col_map[f"rolling_std_{w}"]] = float(np.std(vals))
        if "momentum_1" in col_map:
            new_row[col_map["momentum_1"]] = gv(n) - gv(n - 1)
        if "momentum_7" in col_map:
            new_row[col_map["momentum_7"]] = gv(n) - gv(n - 7)

        window = np.vstack([window[1:], new_row])

    values = [p["prediksi"] for p in predictions]
    return {
        "predictions": predictions,
        "ringkasan": {
            "total": round(float(np.sum(values)), 2),
            "rata_rata": round(float(np.mean(values)), 2),
            "minimum": round(float(np.min(values)), 2),
            "maksimum": round(float(np.max(values)), 2),
        },
    }


def _fallback_forecast(n_days: int, user_transactions: list[dict]) -> dict:
    """Used only if the Keras model fails to load. Produces a simple
    weekday-pattern average from the user's own history so the UI still
    works end-to-end."""
    by_wd: dict[int, list[float]] = {i: [] for i in range(7)}
    for t in user_transactions:
        d = datetime.strptime(t["tanggal"], "%Y-%m-%d")
        by_wd[d.weekday()].append(float(t["nominal"]))
    avg_wd = {wd: (sum(v) / len(v) if v else 0.0) for wd, v in by_wd.items()}
    overall = (
        sum(float(t["nominal"]) for t in user_transactions) / max(1, len(user_transactions))
        if user_transactions
        else 1_000_000.0
    )
    last = (
        max(datetime.strptime(t["tanggal"], "%Y-%m-%d") for t in user_transactions)
        if user_transactions
        else datetime.now()
    )
    preds = []
    for i in range(1, n_days + 1):
        d = last + timedelta(days=i)
        base = avg_wd.get(d.weekday(), 0.0) or overall
        preds.append({
            "tanggal": d.strftime("%Y-%m-%d"),
            "hari": d.strftime("%A"),
            "prediksi": round(base, 2),
        })
    vals = [p["prediksi"] for p in preds]
    return {
        "predictions": preds,
        "ringkasan": {
            "total": round(sum(vals), 2),
            "rata_rata": round(sum(vals) / len(vals), 2),
            "minimum": round(min(vals), 2),
            "maksimum": round(max(vals), 2),
        },
    }
