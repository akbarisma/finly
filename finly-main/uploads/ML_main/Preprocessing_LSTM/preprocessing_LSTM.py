import pandas as pd
import numpy as np
import os
import joblib, os
from sklearn.preprocessing import MinMaxScaler


def load_data(file_path):
    """Load dataset Restaurant."""
    df = pd.read_csv(file_path)
    print(df.head())
    print(df.info())
    return df


def missing_values(df):
    """Tangani missing values (nilai '?' di kolom string & NaN)."""
    df = df.replace('?', np.nan)
    missing = df.isnull().sum()
    print("Missing values per kolom:")
    print(missing[missing > 0])
    df = df.dropna()
    return df


def convert_datetime(df, date_column):
    """Konversi kolom tanggal ke datetime, urutkan, dan jadikan index."""
    df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
    df = df.sort_values(by=date_column)
    df = df.dropna(subset=[date_column])
    df = df.set_index(date_column)
    return df


def feature_selection(df, target_column, drop_cols=None):
    """Pilih fitur numerik yang relevan."""
    if drop_cols is None:
        drop_cols = []
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors='ignore')
    numeric_df = df.select_dtypes(include=[np.number])
    if target_column not in numeric_df.columns:
        raise ValueError(
            f"Target column '{target_column}' tidak numerik atau tidak ada dalam dataframe."
        )
    print(f"Fitur yang digunakan ({len(numeric_df.columns)} kolom):", numeric_df.columns.tolist())
    return numeric_df

def temporal_features(df, target_column):
    """Tambah fitur historis penjualan yang lebih kaya."""
    # Lag harian
    for lag in [1, 2, 3, 7, 14]:
        df[f'lag_{lag}'] = df[target_column].shift(lag)

     # --- Rolling statistics ---
    for window in [7, 14, 30]:
        df[f'rolling_mean_{window}'] = df[target_column].shift(1).rolling(window).mean()
        df[f'rolling_std_{window}']  = df[target_column].shift(1).rolling(window).std()
 
    # --- Momentum (perubahan penjualan) ---
    df['momentum_1'] = df[target_column].diff(1)
    df['momentum_7'] = df[target_column].diff(7)
 
    df = df.dropna()
    print(f"Fitur setelah penambahan temporal: {len(df.columns)} kolom, {len(df)} baris")
    return df

def scaling_data(df):
    """Normalisasi semua kolom ke rentang [0, 1] menggunakan MinMaxScaler."""
    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(df)
    scaled_df = pd.DataFrame(scaled_data, columns=df.columns, index=df.index)
    return scaled_df, scaler

def augment_data(df, target_column, n_augment=2, noise_level=0.01, random_state=42):
   
    np.random.seed(random_state)
 
    augmented_dfs = [df]  # selalu sertakan data asli
 
    for i in range(n_augment):
        df_copy = df.copy()
 
        # Tambah noise hanya ke kolom target (2to5 yang sudah di-scale)
        noise = np.random.normal(
            loc=0,              # rata-rata noise = 0 (tidak menggeser nilai)
            scale=noise_level,  # sebaran noise (±1% dari rentang [0,1])
            size=len(df_copy)
        )
        df_copy[target_column] = df_copy[target_column] + noise
 
        # Pastikan nilai tetap dalam rentang [0, 1] setelah ditambah noise
        df_copy[target_column] = df_copy[target_column].clip(0, 1)
 
        augmented_dfs.append(df_copy)
 
    result = pd.concat(augmented_dfs, ignore_index=True)
 
    print(f"\n=== Hasil Augmentasi ===")
    print(f"Data asli       : {len(df)} baris")
    print(f"Jumlah salinan  : {n_augment}x")
    print(f"Total setelah   : {len(result)} baris ({n_augment + 1}x lipat)")
    print(f"Noise level     : ±{noise_level} (skala 0-1)")
 
    return result

def split_data(df, target_column, test_size=0.2):
    """
    Split data secara temporal (urutan waktu dijaga)
    """
    split_index = int(len(df) * (1 - test_size))
    train = df.iloc[:split_index]
    test  = df.iloc[split_index:]
    X_train = train.drop(columns=[target_column])
    y_train = train[target_column]
    X_test  = test.drop(columns=[target_column])
    y_test  = test[target_column]
    print(f"Train size: {len(X_train)}, Test size: {len(X_test)}")
    return X_train, X_test, y_train, y_test


def save_preprocessed_data(output_dir, x_train, x_test, y_train, y_test):
    """Simpan hasil preprocessing ke folder output."""
    os.makedirs(output_dir, exist_ok=True)
    x_train.to_csv(os.path.join(output_dir, "x_train.csv"), index=False)
    x_test.to_csv(os.path.join(output_dir,  "x_test.csv"),  index=False)
    y_train.to_csv(os.path.join(output_dir, "y_train.csv"), index=False)
    y_test.to_csv(os.path.join(output_dir,  "y_test.csv"),  index=False)
    print(f"Data disimpan ke: {output_dir}")


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # === SESUAIKAN PATH INI ===
    file_path  = r"D:\Financial_Forecast\Data\Restaurant_source\RestaurantDataVets_All_2to5.csv"
    output_dir = r"D:\Financial_Forecast\Data\Restaurant_source\Preprocessed_LSTM"
    scaler_path = r"D:\Financial_Forecast\src\models\lstm_scaler.pkl"
    # ==========================

    target_column = '2to5'
    date_column   = 'DMY'
    drop_cols     = ['Index', 'Group', 'MissingPrevDays']

    df = load_data(file_path)
    df = missing_values(df)
    df = convert_datetime(df, date_column)
    df = feature_selection(df, target_column, drop_cols=drop_cols)

    # Scaling + SIMPAN SCALER
    df, scaler = scaling_data(df)
    os.makedirs(os.path.dirname(scaler_path), exist_ok=True)
    joblib.dump(scaler, scaler_path)
    print(f"Scaler disimpan ke: {scaler_path}")


    df = temporal_features(df, target_column)

    split_index   = int(len(df) * 0.8)
    df_train_asli = df.iloc[:split_index].copy()
    df_test_asli  = df.iloc[split_index:].copy()  # ← tidak pernah diaugmentasi

    df_train_aug = augment_data(df_train_asli, target_column, n_augment=2, noise_level=0.01)

    # pisahkan fitur dan target — TANPA memanggil split_data()
    X_train = df_train_aug.drop(columns=[target_column])  # ← pakai df_train_aug
    y_train = df_train_aug[target_column]
    X_test  = df_test_asli.drop(columns=[target_column])  # ← pakai df_test_asli
    y_test  = df_test_asli[target_column]

    print(f"Train (augmented) : {len(X_train)} baris")  
    print(f"Test  (asli murni): {len(X_test)} baris")    

    # x_train, x_test, y_train, y_test = split_data(df, target_column)
    save_preprocessed_data(output_dir, X_train, X_test, y_train, y_test)
