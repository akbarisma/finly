"""
evaluate.py — Perbandingan LSTM vs Baseline (Regresi Linear)
=============================================================
Output:
- Tabel perbandingan metrik di terminal
- evaluation_report.png
- evaluation_results.csv
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from tensorflow.keras.models import load_model
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import MinMaxScaler
import os
import warnings
warnings.filterwarnings('ignore')


# ─── Konfigurasi ─────────────────────────────────────────────────────────────

# === SESUAIKAN PATH INI ===
RAW_DATA_PATH    = r"D:\Financial_Forecast\Data\Restaurant_source\RestaurantDataVets_All_2to5.csv"
PREPROCESSED_DIR = r"D:\Financial_Forecast\Data\Restaurant_source\Preprocessed_LSTM"
LSTM_MODEL_PATH  = r"D:\Financial_Forecast\src\models\LSTM_model.keras"
OUTPUT_DIR       = r"D:\Financial_Forecast\src\evaluation"
# ==========================

TARGET_COLUMN = '2to5'
DATE_COLUMN   = 'DMY'
DROP_COLS     = ['Index', 'Group', 'MissingPrevDays']
TIME_STEPS    = 14

# Kolom kalender — satu-satunya fitur yang boleh dipakai baseline
CALENDAR_COLS = [
    'Year', 'Day',
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
    'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday',
    'Holiday', 'Carnival', 'LentFasting', 'Ramadan', 'ChristmasSeason'
]


# ─── Helper ──────────────────────────────────────────────────────────────────

def load_preprocessed(preprocessed_dir):
    x_train = pd.read_csv(f"{preprocessed_dir}/x_train.csv")
    x_test  = pd.read_csv(f"{preprocessed_dir}/x_test.csv")
    y_train = pd.read_csv(f"{preprocessed_dir}/y_train.csv")
    y_test  = pd.read_csv(f"{preprocessed_dir}/y_test.csv")
    print(f"Data dimuat — Train: {x_train.shape}, Test: {x_test.shape}")
    return x_train, x_test, y_train, y_test


def make_sequences(x, y, time_steps):
    """Buat sequence 3D untuk LSTM."""
    Xs, Ys = [], []
    for i in range(len(x) - time_steps):
        Xs.append(x.iloc[i:i+time_steps].values)
        Ys.append(y.iloc[i+time_steps].values)
    return np.array(Xs), np.array(Ys)


def load_scaler(raw_path, date_col, drop_cols):
    """Fit ulang scaler dari data mentah untuk inverse transform."""
    df = pd.read_csv(raw_path)
    df = df.replace('?', np.nan).dropna()
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.sort_values(date_col).dropna(subset=[date_col]).set_index(date_col)
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors='ignore')
    df = df.select_dtypes(include=[np.number])
    scaler = MinMaxScaler()
    scaler.fit(df)
    target_idx = df.columns.tolist().index(TARGET_COLUMN)
    n_features  = len(df.columns)
    return scaler, target_idx, n_features


def inverse_transform(values_scaled, scaler, target_idx, n_features):
    """Kembalikan nilai scaled ke satuan penjualan asli."""
    dummy = np.zeros((len(values_scaled), n_features))
    dummy[:, target_idx] = np.array(values_scaled).flatten()
    return scaler.inverse_transform(dummy)[:, target_idx]


def compute_metrics(y_true, y_pred, label):
    mae  = mean_absolute_error(y_true, y_pred)
    mse  = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    r2   = r2_score(y_true, y_pred)
    # MAPE dengan guard division by zero
    mask = np.abs(y_true) > 1e-6
    mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
    return {'Model': label, 'MAE': mae, 'MSE': mse, 'RMSE': rmse,
            'R2': r2, 'MAPE (%)': mape}


def print_comparison(results_df):
    print("\n" + "=" * 65)
    print("          PERBANDINGAN EVALUASI MODEL")
    print("=" * 65)
    print(f"{'Metrik':<12} {'LSTM':>15} {'Baseline (LR)':>18} {'Selisih':>12}")
    print("-" * 65)
    for m in ['MAE', 'MSE', 'RMSE', 'R2', 'MAPE (%)']:
        lstm_val = results_df.loc[results_df['Model']=='LSTM', m].values[0]
        base_val = results_df.loc[results_df['Model']=='Baseline', m].values[0]
        diff = lstm_val - base_val
        sign = '↑' if (m == 'R2' and diff > 0) or (m != 'R2' and diff < 0) else '↓'
        print(f"{m:<12} {lstm_val:>15.4f} {base_val:>18.4f} {diff:>+11.4f} {sign}")
    print("=" * 65)
    lstm_r2 = results_df.loc[results_df['Model']=='LSTM', 'R2'].values[0]
    base_r2 = results_df.loc[results_df['Model']=='Baseline', 'R2'].values[0]
    print()
    if lstm_r2 > base_r2:
        print(f"✓ LSTM lebih baik dari Baseline  (R² {lstm_r2:.4f} > {base_r2:.4f})")
        print(f"  → Model LSTM berhasil menangkap pola temporal yang tidak bisa")
        print(f"    ditangkap oleh regresi linear dengan fitur kalender saja.")
    else:
        print(f"✗ Baseline lebih baik dari LSTM  (R² {base_r2:.4f} > {lstm_r2:.4f})")
        print(f"  → Pertimbangkan hyperparameter tuning atau penambahan fitur.")
    print()


def plot_evaluation(y_true, y_pred_lstm, y_pred_base, results_df, output_dir):
    fig = plt.figure(figsize=(16, 12))
    fig.suptitle('Evaluasi Model: LSTM vs Baseline (Regresi Linear)',
                 fontsize=14, fontweight='bold', y=0.98)
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.4, wspace=0.3)

    # Plot 1: Time series
    ax1 = fig.add_subplot(gs[0, :])
    x_ax = range(len(y_true))
    ax1.plot(x_ax, y_true,      color='black',      linewidth=1.5, label='Aktual',        alpha=0.8)
    ax1.plot(x_ax, y_pred_lstm, color='steelblue',  linewidth=1.5, label='LSTM',          linestyle='--', alpha=0.9)
    ax1.plot(x_ax, y_pred_base, color='darkorange',  linewidth=1.5, label='Baseline (LR)', linestyle=':',  alpha=0.9)
    ax1.set_title('Prediksi vs Aktual — Data Test', fontweight='bold')
    ax1.set_xlabel('Indeks Data Test')
    ax1.set_ylabel('Penjualan (satuan asli)')
    ax1.legend()
    ax1.grid(alpha=0.3)

    # Plot 2: Scatter LSTM
    ax2 = fig.add_subplot(gs[1, 0])
    ax2.scatter(y_true, y_pred_lstm, alpha=0.5, color='steelblue', s=20)
    mn, mx = min(y_true.min(), y_pred_lstm.min()), max(y_true.max(), y_pred_lstm.max())
    ax2.plot([mn, mx], [mn, mx], 'r--', linewidth=1.5)
    r2_lstm = results_df.loc[results_df['Model']=='LSTM', 'R2'].values[0]
    ax2.set_title(f'LSTM — Actual vs Predicted\nR² = {r2_lstm:.4f}', fontweight='bold')
    ax2.set_xlabel('Aktual')
    ax2.set_ylabel('Prediksi')
    ax2.grid(alpha=0.3)

    # Plot 3: Scatter Baseline
    ax3 = fig.add_subplot(gs[1, 1])
    ax3.scatter(y_true, y_pred_base, alpha=0.5, color='darkorange', s=20)
    mn, mx = min(y_true.min(), y_pred_base.min()), max(y_true.max(), y_pred_base.max())
    ax3.plot([mn, mx], [mn, mx], 'r--', linewidth=1.5)
    r2_base = results_df.loc[results_df['Model']=='Baseline', 'R2'].values[0]
    ax3.set_title(f'Baseline (LR) — Actual vs Predicted\nR² = {r2_base:.4f}\n(fitur kalender saja)',
                  fontweight='bold')
    ax3.set_xlabel('Aktual')
    ax3.set_ylabel('Prediksi')
    ax3.grid(alpha=0.3)

    os.makedirs(output_dir, exist_ok=True)
    save_path = os.path.join(output_dir, 'evaluation_report.png')
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()
    print(f"Grafik evaluasi disimpan ke: {save_path}")


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("=" * 55)
    print("      EVALUASI MODEL — LSTM vs BASELINE")
    print("=" * 55)

    # 1. Load data
    x_train, x_test, y_train, y_test = load_preprocessed(PREPROCESSED_DIR)

    # 2. Load scaler
    scaler, target_idx, n_features = load_scaler(RAW_DATA_PATH, DATE_COLUMN, DROP_COLS)

    # ── Evaluasi LSTM ──
    print("\nMemuat model LSTM...")
    lstm_model = load_model(LSTM_MODEL_PATH)
    X_test_seq, y_test_seq = make_sequences(x_test, y_test, TIME_STEPS)
    y_pred_lstm_scaled = lstm_model.predict(X_test_seq, verbose=0).flatten()
    y_true_actual      = inverse_transform(y_test_seq.flatten(), scaler, target_idx, n_features)
    y_pred_lstm_actual = inverse_transform(y_pred_lstm_scaled,   scaler, target_idx, n_features)
    metrics_lstm = compute_metrics(y_true_actual, y_pred_lstm_actual, 'LSTM')

    # ── Evaluasi Baseline ──
    # Baseline hanya pakai kolom kalender (bukan lag/rolling) agar adil.
    # Selain itu, baris x_test diselaraskan dengan output LSTM:
    # LSTM memotong TIME_STEPS baris pertama, baseline harus ikut dipotong
    # agar jumlah sampel sama dan visualisasi tidak error.
    print("\nMelatih model Baseline (fitur kalender saja)...")
    cal_cols    = [c for c in CALENDAR_COLS if c in x_train.columns]
    x_train_cal = x_train[cal_cols]
    x_test_cal  = x_test[cal_cols].iloc[TIME_STEPS:].reset_index(drop=True)
    y_test_cal  = y_test.iloc[TIME_STEPS:].reset_index(drop=True)

    baseline = LinearRegression()
    baseline.fit(x_train_cal, y_train.values.ravel())
    y_pred_base_scaled = baseline.predict(x_test_cal)
    y_pred_base_actual = inverse_transform(y_pred_base_scaled,          scaler, target_idx, n_features)
    y_true_base_actual = inverse_transform(y_test_cal.values.flatten(), scaler, target_idx, n_features)
    metrics_base = compute_metrics(y_true_base_actual, y_pred_base_actual, 'Baseline')

    print(f"Sampel evaluasi: {len(y_true_actual)} titik data")
    print(f"Fitur baseline : {len(cal_cols)} kolom kalender")

    # 3. Bandingkan & tampilkan
    results_df = pd.DataFrame([metrics_lstm, metrics_base])
    print_comparison(results_df)

    # 4. Simpan CSV
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    csv_path = os.path.join(OUTPUT_DIR, 'evaluation_results.csv')
    results_df.to_csv(csv_path, index=False)
    print(f"Hasil evaluasi disimpan ke: {csv_path}")

    # 5. Grafik
    plot_evaluation(y_true_actual, y_pred_lstm_actual, y_pred_base_actual,
                    results_df, OUTPUT_DIR)
