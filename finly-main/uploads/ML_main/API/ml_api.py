"""
ml_api.py — Flask API Server untuk Model LSTM
===============================================
Server ini menjadi jembatan antara backend PHP dan model ML Python.

Cara kerja:
1. Backend PHP mengirim POST request ke server ini
2. Server memuat model LSTM dan menjalankan forecasting
3. Hasil prediksi dikembalikan sebagai JSON ke PHP
4. PHP meneruskan data ke frontend React

Server berjalan di: http://localhost:5000
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import numpy as np
from tensorflow.keras.models import load_model
from sklearn.preprocessing import MinMaxScaler
import warnings
import os

warnings.filterwarnings('ignore')

app = Flask(__name__)
CORS(app)  # Izinkan request dari PHP/React

# ─── Konfigurasi Path ────────────────────────────────────────────────────────
# === SESUAIKAN PATH INI ===
BASE_DIR      = r"D:\Financial_Forecast"
RAW_DATA_PATH = os.path.join(BASE_DIR, "Data", "Restaurant_source", "RestaurantDataVets_All_2to5.csv")
MODEL_PATH    = os.path.join(BASE_DIR, "ML_main", "models", "LSTM_model.keras")
# ==========================

TARGET_COLUMN = '2to5'
DATE_COLUMN   = 'DMY'
DROP_COLS     = ['Index', 'Group', 'MissingPrevDays']
TIME_STEPS    = 14

# Cache model agar tidak dimuat ulang setiap request
_model  = None
_scaler = None
_df_raw = None

CALENDAR_COLS = [
    'Year', 'Day', 'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
    'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday',
    'Holiday', 'Carnival', 'LentFasting', 'Ramadan', 'ChristmasSeason'
]


# ─── Helper ──────────────────────────────────────────────────────────────────

def get_model():
    global _model
    if _model is None:
        print("Memuat model LSTM...")
        _model = load_model(MODEL_PATH)
        print("Model berhasil dimuat.")
    return _model


def get_scaler_and_data():
    global _scaler, _df_raw
    if _scaler is None:
        print("Memuat data dan scaler...")
        df = pd.read_csv(RAW_DATA_PATH)
        df = df.replace('?', np.nan).dropna()
        df[DATE_COLUMN] = pd.to_datetime(df[DATE_COLUMN], errors='coerce')
        df = df.sort_values(DATE_COLUMN).dropna(subset=[DATE_COLUMN])
        df = df.set_index(DATE_COLUMN)
        df = df.drop(columns=[c for c in DROP_COLS if c in df.columns], errors='ignore')
        df = df.select_dtypes(include=[np.number])
        _df_raw = df.copy()
        _scaler = MinMaxScaler()
        _scaler.fit(df)
    return _scaler, _df_raw


def add_temporal_features(df_scaled, target_column):
    for lag in [1, 2, 3, 7, 14]:  # harus cocok dengan model (39 fitur)
        df_scaled[f'lag_{lag}'] = df_scaled[target_column].shift(lag)
    for window in [7, 14, 30]:
        df_scaled[f'rolling_mean_{window}'] = df_scaled[target_column].shift(1).rolling(window).mean()
        df_scaled[f'rolling_std_{window}']  = df_scaled[target_column].shift(1).rolling(window).std()
    df_scaled['momentum_1'] = df_scaled[target_column].diff(1)
    df_scaled['momentum_7'] = df_scaled[target_column].diff(7)
    df_scaled = df_scaled.dropna()
    return df_scaled


def inverse_transform_single(val, scaler, target_idx, n_features):
    dummy = np.zeros((1, n_features))
    dummy[0, target_idx] = val
    return float(scaler.inverse_transform(dummy)[0, target_idx])


def run_forecast(n_days, user_transactions=None):
    
    model  = get_model()
    scaler, df_raw = get_scaler_and_data()
    target_idx = df_raw.columns.tolist().index(TARGET_COLUMN)
    n_features  = len(df_raw.columns)

    # Jika ada data transaksi dari user Snappoint, append ke df_raw
    if user_transactions and len(user_transactions) > 0:
        try:
            df_user = pd.DataFrame(user_transactions)
            df_user['tanggal'] = pd.to_datetime(df_user['tanggal'])
            df_user = df_user.set_index('tanggal')
            df_user = df_user.rename(columns={'nominal': TARGET_COLUMN})
            # Isi kolom lain dengan 0 (tidak ada info kalender dari transaksi user)
            for col in df_raw.columns:
                if col not in df_user.columns:
                    df_user[col] = 0
            df_combined = pd.concat([df_raw, df_user[df_raw.columns]])
            df_combined = df_combined[~df_combined.index.duplicated(keep='last')]
            df_combined = df_combined.sort_index()
        except Exception:
            df_combined = df_raw
    else:
        df_combined = df_raw

    # Scale dan tambah temporal features
    scaled_arr = scaler.transform(df_combined)
    df_scaled  = pd.DataFrame(scaled_arr, columns=df_combined.columns, index=df_combined.index)
    df_feat    = add_temporal_features(df_scaled.copy(), TARGET_COLUMN)

    all_columns = df_feat.columns.tolist()
    window      = df_feat.values[-TIME_STEPS:].copy()
    history     = list(df_feat[TARGET_COLUMN].values[-(max(TIME_STEPS, 30) + 5):])

    predictions = []
    last_date   = df_feat.index[-1]

    for day in range(n_days):
        inp      = window.reshape(1, TIME_STEPS, len(all_columns))
        pred_sc  = float(model.predict(inp, verbose=0)[0][0])
        pred_val = inverse_transform_single(pred_sc, scaler, target_idx, n_features)
        future_date = last_date + pd.Timedelta(days=day + 1)

        predictions.append({
            'tanggal'  : future_date.strftime('%Y-%m-%d'),
            'hari'     : future_date.strftime('%A'),
            'prediksi' : round(pred_val, 2)
        })

        # Update window
        new_row = window[-1].copy()
        new_row[all_columns.index(TARGET_COLUMN)] = pred_sc
        history.append(pred_sc)

        col_map = {c: i for i, c in enumerate(all_columns)}
        n = len(history) - 1
        def gv(i): return history[i] if i >= 0 else 0.0

        for lag in [1, 2, 3, 7, 14]:  # harus cocok dengan model (39 fitur)
            if f'lag_{lag}' in col_map:
                new_row[col_map[f'lag_{lag}']] = gv(n - lag + 1)
        for w in [7, 14, 30]:
            vals = [gv(n - w + 1 + i) for i in range(w)]
            if f'rolling_mean_{w}' in col_map:
                new_row[col_map[f'rolling_mean_{w}']] = float(np.mean(vals))
            if f'rolling_std_{w}' in col_map:
                new_row[col_map[f'rolling_std_{w}']]  = float(np.std(vals))
        if 'momentum_1' in col_map:
            new_row[col_map['momentum_1']] = gv(n) - gv(n - 1)
        if 'momentum_7' in col_map:
            new_row[col_map['momentum_7']] = gv(n) - gv(n - 7)

        window = np.vstack([window[1:], new_row])

    return predictions


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health():
    """Cek apakah server ML aktif."""
    return jsonify({'status': 'ok', 'message': 'ML API aktif'})


@app.route('/forecast', methods=['POST'])
def forecast():
    try:
        body             = request.get_json(force=True) or {}
        n_days           = int(body.get('n_days', 30))
        user_transactions = body.get('transactions', [])

        n_days = max(1, min(n_days, 90))  # batasi 1–90 hari

        predictions = run_forecast(n_days, user_transactions)

        values = [p['prediksi'] for p in predictions]
        return jsonify({
            'status'       : 'success',
            'n_days'       : n_days,
            'predictions'  : predictions,
            'ringkasan'    : {
                'rata_rata': round(float(np.mean(values)), 2),
                'minimum'  : round(float(np.min(values)),  2),
                'maksimum' : round(float(np.max(values)),  2),
                'total'    : round(float(np.sum(values)),  2),
            }
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ─── Run ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 50)
    print("  ML API Server — Snappoint Forecasting")
    print("  http://localhost:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False)
