"""
utils.py — Fungsi Utilitas: Simpan & Muat Scaler + Model
=========================================================
Mengatasi masalah scaler yang belum disimpan.
Scaler WAJIB disimpan bersama model agar inverse transform
saat forecasting menghasilkan nilai yang benar.

Gunakan fungsi ini dari preprocessing_LSTM.py dan forecasting.py.
"""

import pandas as pd
import numpy as np
import joblib
import os
from sklearn.preprocessing import MinMaxScaler


# ─── Konfigurasi default ─────────────────────────────────────────────────────

TARGET_COLUMN = '2to5'
DATE_COLUMN   = 'DMY'
DROP_COLS     = ['Index', 'Group', 'MissingPrevDays']


# ─── Scaler ──────────────────────────────────────────────────────────────────

def fit_and_save_scaler(raw_data_path, scaler_path,
                         date_col=DATE_COLUMN, drop_cols=DROP_COLS,
                         target_col=TARGET_COLUMN):
    """
    Fit MinMaxScaler pada data mentah asli dan simpan ke disk.

    PENTING: Scaler harus di-fit pada data mentah SEBELUM temporal features
    ditambahkan, agar konsisten dengan urutan kolom saat training.

    Dipanggil dari: preprocessing_LSTM.py saat __main__ dijalankan.
    """
    df = pd.read_csv(raw_data_path)
    df = df.replace('?', np.nan).dropna()
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.sort_values(date_col).dropna(subset=[date_col]).set_index(date_col)
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors='ignore')
    df = df.select_dtypes(include=[np.number])

    scaler = MinMaxScaler()
    scaler.fit(df)

    os.makedirs(os.path.dirname(scaler_path), exist_ok=True)
    joblib.dump(scaler, scaler_path)

    target_idx = df.columns.tolist().index(target_col)
    n_features  = len(df.columns)

    print(f"Scaler disimpan ke : {scaler_path}")
    print(f"Target index       : {target_idx} (kolom '{target_col}')")
    print(f"Jumlah fitur       : {n_features}")
    print(f"Range target       : {scaler.data_min_[target_idx]:.2f} – "
          f"{scaler.data_max_[target_idx]:.2f}")

    return scaler, target_idx, n_features


def load_scaler(scaler_path):
    """
    Muat scaler yang sudah disimpan dari disk.

    Dipanggil dari: forecasting.py dan evaluate.py.
    """
    if not os.path.exists(scaler_path):
        raise FileNotFoundError(
            f"Scaler tidak ditemukan di: {scaler_path}\n"
            f"Jalankan preprocessing_LSTM.py terlebih dahulu untuk membuat scaler."
        )
    scaler = joblib.load(scaler_path)
    print(f"Scaler dimuat dari: {scaler_path}")
    return scaler


def inverse_transform_target(values_scaled, scaler, target_idx, n_features):
    """
    Kembalikan nilai scaled (0–1) ke satuan asli penjualan.

    Parameters:
    - values_scaled : array 1D nilai prediksi dalam skala [0, 1]
    - scaler        : MinMaxScaler yang sudah di-fit
    - target_idx    : index kolom target dalam scaler
    - n_features    : total jumlah fitur dalam scaler

    Returns:
    - array 1D nilai dalam satuan asli (misal: 500–2800)
    """
    dummy = np.zeros((len(values_scaled), n_features))
    dummy[:, target_idx] = np.array(values_scaled).flatten()
    return scaler.inverse_transform(dummy)[:, target_idx]


# ─── Model info ──────────────────────────────────────────────────────────────

def get_scaler_info(scaler, target_col, raw_data_path,
                     date_col=DATE_COLUMN, drop_cols=DROP_COLS):
    """
    Ambil target_idx dan n_features dari scaler yang sudah dimuat.
    Digunakan saat scaler dimuat dari file (bukan di-fit ulang).
    """
    df = pd.read_csv(raw_data_path)
    df = df.replace('?', np.nan).dropna()
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.sort_values(date_col).dropna(subset=[date_col]).set_index(date_col)
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors='ignore')
    df = df.select_dtypes(include=[np.number])

    target_idx = df.columns.tolist().index(target_col)
    n_features  = len(df.columns)
    return target_idx, n_features


# ─── Validasi konsistensi ─────────────────────────────────────────────────────

def validate_consistency(preprocessed_dir, scaler_path, raw_data_path,
                          date_col=DATE_COLUMN, drop_cols=DROP_COLS,
                          target_col=TARGET_COLUMN):
    """
    Periksa apakah jumlah kolom preprocessed konsisten dengan scaler.
    Jalankan ini jika muncul error dimensi saat forecasting.
    """
    print("=== Validasi Konsistensi ===")

    # Cek preprocessed
    x_train = pd.read_csv(f"{preprocessed_dir}/x_train.csv")
    print(f"Kolom x_train    : {x_train.shape[1]}")

    # Cek scaler
    if os.path.exists(scaler_path):
        scaler = joblib.load(scaler_path)
        print(f"Fitur scaler     : {scaler.n_features_in_}")
    else:
        print("Scaler belum ada!")

    # Cek raw data
    df = pd.read_csv(raw_data_path)
    df = df.replace('?', np.nan).dropna()
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.sort_values(date_col).dropna(subset=[date_col]).set_index(date_col)
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors='ignore')
    df = df.select_dtypes(include=[np.number])
    print(f"Kolom raw data   : {len(df.columns)}")
    print(f"Target index     : {df.columns.tolist().index(target_col)}")

    print("\nKolom raw (sebelum temporal features):")
    for i, col in enumerate(df.columns):
        marker = ' ← TARGET' if col == target_col else ''
        print(f"  [{i:02d}] {col}{marker}")
