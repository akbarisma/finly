"""
hyperparameter_tuning.py — Pencarian Hyperparameter Sistematis
==============================================================
Mencari kombinasi TIME_STEPS, LSTM units, Dropout, dan batch_size
terbaik menggunakan grid search manual.

Cara kerja:
- Setiap kombinasi hyperparameter dilatih dan dievaluasi
- Hasil disimpan ke CSV untuk dibandingkan
- Konfigurasi terbaik dicetak di akhir

PERHATIAN: Proses ini memakan waktu lama (30–90 menit tergantung GPU/CPU).
Kurangi jumlah kombinasi di PARAM_GRID jika ingin lebih cepat.

Jalankan:
    python src/models/hyperparameter_tuning.py
"""

import pandas as pd
import numpy as np
import os
import time
import itertools
import warnings
warnings.filterwarnings('ignore')

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error


# ─── Konfigurasi ─────────────────────────────────────────────────────────────

# === SESUAIKAN PATH INI ===
PREPROCESSED_DIR = r"D:\Financial_Forecast\Data\Restaurant_source\Preprocessed_LSTM"
OUTPUT_DIR       = r"D:\Financial_Forecast\src\models"
# ==========================

# Grid kombinasi yang akan dicoba
# Kurangi jumlah nilai di tiap list untuk mempercepat proses
PARAM_GRID = {
    'time_steps' : [7, 14, 21],       # panjang jendela waktu
    'units'      : [64, 128],          # jumlah unit LSTM layer pertama
    'dropout'    : [0.1, 0.2],         # dropout rate
    'batch_size' : [16, 32],           # ukuran batch
}

# Training config (tetap untuk semua kombinasi)
EPOCHS   = 150    # Early stopping akan hentikan lebih awal
PATIENCE = 20


# ─── Helper ──────────────────────────────────────────────────────────────────

def load_data(preprocessed_dir):
    x_train = pd.read_csv(f"{preprocessed_dir}/x_train.csv")
    x_test  = pd.read_csv(f"{preprocessed_dir}/x_test.csv")
    y_train = pd.read_csv(f"{preprocessed_dir}/y_train.csv")
    y_test  = pd.read_csv(f"{preprocessed_dir}/y_test.csv")
    return x_train, x_test, y_train, y_test


def make_sequences(x, y, time_steps):
    Xs, Ys = [], []
    for i in range(len(x) - time_steps):
        Xs.append(x.iloc[i:i+time_steps].values)
        Ys.append(y.iloc[i+time_steps].values)
    return np.array(Xs), np.array(Ys)


def build_model(input_shape, units, dropout):
    """
    Bangun model LSTM dengan konfigurasi yang bisa divariasikan.
    - Layer 1: units LSTM
    - Layer 2: units//2 LSTM
    - Dense 32 + output
    """
    model = Sequential([
        LSTM(units,      return_sequences=True, input_shape=input_shape),
        Dropout(dropout),
        LSTM(units // 2, return_sequences=False),
        Dropout(dropout),
        Dense(32, activation='relu'),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mean_squared_error')
    return model


def train_and_evaluate(x_train, x_test, y_train, y_test,
                        time_steps, units, dropout, batch_size):
    """Latih satu konfigurasi dan kembalikan metriknya."""
    # Buat sequence
    X_tr, y_tr = make_sequences(x_train, y_train, time_steps)
    X_te, y_te = make_sequences(x_test,  y_test,  time_steps)

    if len(X_tr) == 0 or len(X_te) == 0:
        return None

    # Bangun & latih model
    model = build_model((X_tr.shape[1], X_tr.shape[2]), units, dropout)

    early_stop = EarlyStopping(monitor='val_loss', patience=PATIENCE,
                               restore_best_weights=True, verbose=0)
    reduce_lr  = ReduceLROnPlateau(monitor='val_loss', factor=0.5,
                                   patience=10, min_lr=1e-6, verbose=0)

    start = time.time()
    history = model.fit(
        X_tr, y_tr,
        validation_data=(X_te, y_te),
        epochs=EPOCHS,
        batch_size=batch_size,
        callbacks=[early_stop, reduce_lr],
        verbose=0
    )
    elapsed = time.time() - start

    # Evaluasi
    y_pred = model.predict(X_te, verbose=0).flatten()
    mae  = mean_absolute_error(y_te.flatten(), y_pred)
    rmse = np.sqrt(mean_squared_error(y_te.flatten(), y_pred))
    r2   = r2_score(y_te.flatten(), y_pred)

    best_epoch    = np.argmin(history.history['val_loss']) + 1
    best_val_loss = min(history.history['val_loss'])

    return {
        'time_steps'   : time_steps,
        'units'        : units,
        'dropout'      : dropout,
        'batch_size'   : batch_size,
        'best_epoch'   : best_epoch,
        'val_loss'     : round(best_val_loss, 6),
        'MAE'          : round(mae,  4),
        'RMSE'         : round(rmse, 4),
        'R2'           : round(r2,   4),
        'waktu_detik'  : round(elapsed, 1),
    }


def print_progress(i, total, params, result):
    bar_len = 30
    filled  = int(bar_len * i / total)
    bar     = '█' * filled + '░' * (bar_len - filled)
    print(f"\r[{bar}] {i}/{total} | ts={params['time_steps']} "
          f"u={params['units']} dr={params['dropout']} "
          f"bs={params['batch_size']} | R²={result['R2']:.4f}", end='', flush=True)


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("=" * 60)
    print("      HYPERPARAMETER TUNING — GRID SEARCH")
    print("=" * 60)

    # 1. Load data
    x_train, x_test, y_train, y_test = load_data(PREPROCESSED_DIR)
    print(f"Data dimuat — Train: {x_train.shape}, Test: {x_test.shape}")

    # 2. Buat semua kombinasi
    keys   = list(PARAM_GRID.keys())
    values = list(PARAM_GRID.values())
    combos = list(itertools.product(*values))
    total  = len(combos)
    print(f"Total kombinasi: {total}")
    print(f"Estimasi waktu : {total * 2}–{total * 5} menit\n")

    # 3. Jalankan grid search
    results = []
    for i, combo in enumerate(combos, 1):
        params = dict(zip(keys, combo))
        result = train_and_evaluate(
            x_train, x_test, y_train, y_test,
            **params
        )
        if result:
            results.append(result)
            print_progress(i, total, params, result)

    print()  # newline setelah progress bar

    # 4. Tampilkan hasil
    results_df = pd.DataFrame(results).sort_values('R2', ascending=False)

    print("\n=== TOP 5 KONFIGURASI TERBAIK (berdasarkan R²) ===")
    print(results_df.head(5).to_string(index=False))

    print("\n=== KONFIGURASI TERBAIK ===")
    best = results_df.iloc[0]
    print(f"  TIME_STEPS : {int(best['time_steps'])}")
    print(f"  UNITS      : {int(best['units'])}")
    print(f"  DROPOUT    : {best['dropout']}")
    print(f"  BATCH_SIZE : {int(best['batch_size'])}")
    print(f"  R²         : {best['R2']:.4f}")
    print(f"  RMSE       : {best['RMSE']:.4f}")
    print(f"  Best Epoch : {int(best['best_epoch'])}")
    print()
    print("→ Salin nilai di atas ke LSTM_model.py bagian __main__")

    # 5. Simpan semua hasil ke CSV
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    csv_path = os.path.join(OUTPUT_DIR, 'tuning_results.csv')
    results_df.to_csv(csv_path, index=False)
    print(f"\nSeluruh hasil disimpan ke: {csv_path}")
