"""
forecasting.py
==============
Modul untuk meramalkan penjualan restoran (kolom '2to5') N hari ke depan
menggunakan model LSTM yang sudah dilatih.
 
Jalankan:
    python forecasting.py
"""
 
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from tensorflow.keras.models import load_model
from sklearn.preprocessing import MinMaxScaler
import warnings
import os
 
warnings.filterwarnings('ignore')
 
 
# ─── Konfigurasi ─────────────────────────────────────────────────────────────
 
# === SESUAIKAN PATH INI ===
RAW_DATA_PATH = r"D:\Financial_Forecast\Data\Restaurant_source\RestaurantDataVets_All_2to5_Differenced.csv"
MODEL_PATH    = r"D:\Financial_Forecast\src\models\LSTM_model.keras"
OUTPUT_DIR    = r"D:\Financial_Forecast\src\models"
# ==========================
 
TARGET_COLUMN = '2to5'
DATE_COLUMN   = 'DMY'
DROP_COLS     = ['Index', 'Group', 'MissingPrevDays']
TIME_STEPS    = 14
N_FORECAST    = 30
 
 
# ─── Fungsi Helper ───────────────────────────────────────────────────────────
 
def load_and_prepare_data(file_path, target_column, date_column, drop_cols):
    df = pd.read_csv(file_path)
    df = df.replace('?', np.nan).dropna()
    df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
    df = df.sort_values(date_column).dropna(subset=[date_column])
    df = df.set_index(date_column)
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors='ignore')
    df = df.select_dtypes(include=[np.number])
    print(f"Data historis dimuat: {len(df)} baris")
    print(f"Periode: {df.index.min().date()} s/d {df.index.max().date()}")
    return df
 
 
def fit_scaler(df):
    scaler = MinMaxScaler()
    scaler.fit(df)
    target_idx = df.columns.tolist().index(TARGET_COLUMN)
    print(f"Scaler di-fit pada {df.shape[1]} kolom")
    print(f"Range target '{TARGET_COLUMN}': {scaler.data_min_[target_idx]:.2f} - {scaler.data_max_[target_idx]:.2f}")
    return scaler, target_idx
 
 
def add_temporal_features(df_scaled, target_column):
    """
    Tambah fitur temporal — HARUS identik dengan preprocessing_LSTM.py.
    Lag yang dipakai: [1, 2, 3, 7, 14] → menghasilkan 39 fitur total (tanpa target).
 
    CATATAN: Fungsi ini mempertahankan kolom target (2to5) di df_scaled
    agar bisa dipakai untuk menghitung history di forecast_future.
    Kolom target akan DIBUANG sebelum dikirim ke model (lihat forecast_future).
    """
    for lag in [1, 2, 3, 7, 14]:
        df_scaled[f'lag_{lag}'] = df_scaled[target_column].shift(lag)
 
    for window in [7, 14, 30]:
        df_scaled[f'rolling_mean_{window}'] = df_scaled[target_column].shift(1).rolling(window).mean()
        df_scaled[f'rolling_std_{window}']  = df_scaled[target_column].shift(1).rolling(window).std()
 
    df_scaled['momentum_1'] = df_scaled[target_column].diff(1)
    df_scaled['momentum_7'] = df_scaled[target_column].diff(7)
 
    df_scaled = df_scaled.dropna()
    return df_scaled
 
 
def inverse_transform_target(scaled_value, scaler, target_idx, n_features):
    dummy = np.zeros((1, n_features))
    dummy[0, target_idx] = scaled_value
    return scaler.inverse_transform(dummy)[0, target_idx]
 
 
def update_temporal_features(row, history_scaled, feature_columns):
    """
    Update fitur temporal pada baris baru.
 
    PERUBAHAN: parameter all_columns diganti feature_columns (tanpa target)
    agar indexing kolom konsisten dengan window yang sudah dibuang targetnya.
    """
    col_map = {col: i for i, col in enumerate(feature_columns)}
 
    def get_val(idx):
        return history_scaled[idx] if idx >= 0 else 0.0
 
    n = len(history_scaled) - 1
 
    for lag in [1, 2, 3, 7, 14]:
        col = f'lag_{lag}'
        if col in col_map:
            row[col_map[col]] = get_val(n - lag + 1)
 
    for window in [7, 14, 30]:
        mean_col = f'rolling_mean_{window}'
        std_col  = f'rolling_std_{window}'
        window_vals = [get_val(n - window + 1 + i) for i in range(window)]
        if mean_col in col_map:
            row[col_map[mean_col]] = np.mean(window_vals)
        if std_col in col_map:
            row[col_map[std_col]] = np.std(window_vals) if len(window_vals) > 1 else 0.0
 
    if 'momentum_1' in col_map:
        row[col_map['momentum_1']] = get_val(n) - get_val(n - 1)
    if 'momentum_7' in col_map:
        row[col_map['momentum_7']] = get_val(n) - get_val(n - 7)
 
    return row
 
 
def forecast_future(model, df_with_features, scaler, target_idx, n_forecast, time_steps):
    """
    Forecasting N hari ke depan secara rekursif.
 
    PERBAIKAN UTAMA (dibanding versi sebelumnya):
    - df_with_features berisi 40 kolom (39 fitur + 1 target '2to5')
    - Window yang dikirim ke model hanya 39 kolom TANPA target
    - Ini sesuai dengan x_train saat training yang juga tanpa kolom target
    """
    target_col = TARGET_COLUMN
 
    # ── PERUBAHAN 1: Pisahkan fitur dan target sebelum membuat window ──
    # df_with_features memiliki 40 kolom (termasuk '2to5')
    # Model hanya boleh menerima 39 kolom (TANPA '2to5')
    feature_cols    = [c for c in df_with_features.columns if c != target_col]
    df_features_only = df_with_features[feature_cols]   # 39 kolom, tanpa target
    n_features       = len(feature_cols)                # = 39
 
    print(f"Fitur yang dikirim ke model: {n_features} kolom (tanpa '{target_col}')")
 
    # ── PERUBAHAN 2: Window dibuat dari df_features_only (39 kolom) ──
    window = df_features_only.values[-time_steps:].copy()  # shape: (time_steps, 39)
 
    # History target untuk menghitung lag/rolling pada iterasi berikutnya
    history_len    = max(time_steps, 30) + n_forecast + 5
    history_scaled = list(df_with_features[target_col].values[-history_len:])
 
    predictions_scaled = []
    predictions_actual = []
 
    print(f"\nMemulai forecasting {n_forecast} hari ke depan...")
    print("-" * 40)
 
    for day in range(n_forecast):
        # Input ke model: (1, time_steps, 39) — TANPA kolom target
        input_seq   = window.reshape(1, time_steps, n_features)
        pred_scaled = model.predict(input_seq, verbose=0)[0][0]
        pred_actual = inverse_transform_target(
            pred_scaled, scaler, target_idx,
            len(scaler.scale_)   # n_features scaler = 27 (kolom raw sebelum temporal)
        )
 
        predictions_scaled.append(pred_scaled)
        predictions_actual.append(pred_actual)
 
        # Buat baris baru: salin fitur kalender dari hari terakhir
        new_row = window[-1].copy()   # shape: (39,) — sudah tanpa target
 
        # Tambahkan prediksi ke history target
        history_scaled.append(pred_scaled)
 
        # ── PERUBAHAN 3: update_temporal_features pakai feature_cols bukan all_columns ──
        new_row = update_temporal_features(new_row, history_scaled, feature_cols)
 
        # Geser window maju 1 hari
        window = np.vstack([window[1:], new_row])
 
        print(f"  Hari +{day+1:02d}: {pred_actual:8.2f} (scaled: {pred_scaled:.4f})")
 
    return predictions_scaled, predictions_actual
 
 
def generate_future_dates(last_date, n_days):
    return pd.date_range(
        start=last_date + pd.Timedelta(days=1), periods=n_days, freq='D'
    )
 
 
def visualize_forecast(df_actual, future_dates, predictions_actual,
                       n_history=90, output_dir="."):
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
 
    ax1 = axes[0]
    history_plot = df_actual[TARGET_COLUMN].iloc[-n_history:]
    ax1.plot(history_plot.index, history_plot.values,
             color='steelblue', linewidth=1.5, label='Data Historis Aktual')
    ax1.plot(future_dates, predictions_actual,
             color='darkorange', linewidth=2, linestyle='--',
             marker='o', markersize=4, label='Prediksi Masa Depan')
    ax1.axvline(x=df_actual.index[-1], color='gray', linestyle=':', linewidth=1.5,
                label='Hari Ini')
    ax1.axvspan(future_dates[0], future_dates[-1],
                alpha=0.08, color='darkorange', label='Periode Prediksi')
    ax1.set_title(f'Prediksi Penjualan — {len(predictions_actual)} Hari ke Depan',
                  fontsize=14, fontweight='bold')
    ax1.set_xlabel('Tanggal')
    ax1.set_ylabel('Penjualan (2to5)')
    ax1.legend(loc='upper left')
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=30, ha='right')
    ax1.grid(alpha=0.3)
 
    ax2 = axes[1]
    bars = ax2.bar(range(len(predictions_actual)), predictions_actual,
                   color='darkorange', alpha=0.8, edgecolor='white')
    for i, (bar, val) in enumerate(zip(bars, predictions_actual)):
        if i % 5 == 0 or i == len(predictions_actual) - 1:
            ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 5,
                     f'{val:.0f}', ha='center', va='bottom', fontsize=8)
    avg_pred = np.mean(predictions_actual)
    ax2.axhline(y=avg_pred, color='red', linestyle='--', linewidth=1.5,
                label=f'Rata-rata: {avg_pred:.0f}')
    ax2.set_title('Detail Prediksi Per Hari', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Hari ke-')
    ax2.set_ylabel('Penjualan Prediksi (2to5)')
    ax2.set_xticks(range(len(future_dates)))
    ax2.set_xticklabels([d.strftime('%m/%d') for d in future_dates],
                        rotation=45, ha='right', fontsize=8)
    ax2.legend()
    ax2.grid(alpha=0.3, axis='y')
 
    plt.tight_layout()
    save_path = os.path.join(output_dir, 'forecast_results.png')
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()
    print(f"\nGrafik disimpan ke: {save_path}")
 
 
def save_forecast_to_csv(future_dates, predictions_actual, output_dir="."):
    df_forecast = pd.DataFrame({
        'Tanggal'            : future_dates,
        'Prediksi_Penjualan' : [round(v, 2) for v in predictions_actual],
        'Hari'               : [d.strftime('%A') for d in future_dates]
    })
    save_path = os.path.join(output_dir, 'forecast_results.csv')
    df_forecast.to_csv(save_path, index=False)
    print(f"Hasil prediksi disimpan ke: {save_path}")
    return df_forecast
 
 
def print_forecast_summary(future_dates, predictions_actual):
    print("\n" + "=" * 55)
    print("         RINGKASAN HASIL FORECASTING")
    print("=" * 55)
    print(f"{'Tanggal':<15} {'Hari':<12} {'Prediksi Penjualan':>20}")
    print("-" * 55)
    for date, pred in zip(future_dates, predictions_actual):
        print(f"{date.strftime('%Y-%m-%d'):<15} {date.strftime('%A'):<12} {pred:>18.2f}")
    print("-" * 55)
    print(f"{'Rata-rata':<27} {np.mean(predictions_actual):>18.2f}")
    print(f"{'Minimum'  :<27} {np.min(predictions_actual):>18.2f}")
    print(f"{'Maksimum' :<27} {np.max(predictions_actual):>18.2f}")
    print("=" * 55)
 
 
# ─── Main ────────────────────────────────────────────────────────────────────
 
if __name__ == "__main__":
 
    print("=" * 55)
    print("      FORECASTING PENJUALAN RESTORAN (LSTM)")
    print("=" * 55)
 
    # 1. Load data historis
    df_raw = load_and_prepare_data(RAW_DATA_PATH, TARGET_COLUMN, DATE_COLUMN, DROP_COLS)
 
    # 2. Fit scaler
    scaler, target_idx = fit_scaler(df_raw)
 
    # 3. Scale data
    scaled_arr = scaler.transform(df_raw)
    df_scaled  = pd.DataFrame(scaled_arr, columns=df_raw.columns, index=df_raw.index)
 
    # 4. Tambah fitur temporal
    # df_features memiliki 40 kolom: 26 kalender + 1 target (2to5) + 13 temporal
    df_features = add_temporal_features(df_scaled.copy(), TARGET_COLUMN)
    print(f"\nTotal kolom df_features : {df_features.shape[1]}")
    print(f"Kolom fitur (tanpa target): {df_features.shape[1] - 1}  ← yang dikirim ke model")
 
    # 5. Load model
    print(f"\nMemuat model dari: {MODEL_PATH}")
    model = load_model(MODEL_PATH)
    print("Model berhasil dimuat.")
 
    # 6. Forecasting
    _, predictions_actual = forecast_future(
        model            = model,
        df_with_features = df_features,
        scaler           = scaler,
        target_idx       = target_idx,
        n_forecast       = N_FORECAST,
        time_steps       = TIME_STEPS
    )
 
    # 7. Tanggal prediksi
    last_date    = df_raw.index[-1]
    future_dates = generate_future_dates(last_date, N_FORECAST)
 
    # 8. Output
    print_forecast_summary(future_dates, predictions_actual)
    save_forecast_to_csv(future_dates, predictions_actual, OUTPUT_DIR)
    visualize_forecast(df_raw, future_dates, predictions_actual,
                       n_history=90, output_dir=OUTPUT_DIR)