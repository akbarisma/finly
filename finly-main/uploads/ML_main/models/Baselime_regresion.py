import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import joblib
import os
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error


CALENDAR_COLS = [
    'Year', 'Day',
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
    'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday',
    'Holiday', 'Carnival', 'LentFasting', 'Ramadan', 'ChristmasSeason'
]


def load_data(preprocessed_dir):
    """Load data hasil preprocessing untuk baseline regression."""
    x_train = pd.read_csv(f"{preprocessed_dir}/x_train.csv")
    x_test  = pd.read_csv(f"{preprocessed_dir}/x_test.csv")
    y_train = pd.read_csv(f"{preprocessed_dir}/y_train.csv")
    y_test  = pd.read_csv(f"{preprocessed_dir}/y_test.csv")

    print("Shape x_train:", x_train.shape)
    print("Shape x_test :", x_test.shape)
    return x_train, x_test, y_train, y_test


def filter_calendar_features(x_train, x_test):
    """
    Saring hanya kolom kalender dari dataset preprocessed LSTM.

    Mengapa diperlukan:
    Dataset Preprocessed_LSTM berisi fitur lag, rolling mean, momentum
    yang dihitung dari nilai target (2to5) masa lalu. Jika baseline
    menggunakan fitur-fitur ini, model langsung 'tahu' nilai penjualan
    kemarin dan bisa memprediksi hari ini dengan sempurna (R² mendekati 1.0).

    Baseline yang valid hanya memakai fitur kalender — informasi yang
    benar-benar tersedia sebelum penjualan terjadi.
    """
    # Ambil kolom kalender yang ada di dataset
    cols_train = [c for c in CALENDAR_COLS if c in x_train.columns]
    cols_test  = [c for c in CALENDAR_COLS if c in x_test.columns]

    x_train_cal = x_train[cols_train]
    x_test_cal  = x_test[cols_test]

    print(f"Fitur baseline (kalender saja): {len(cols_train)} kolom")
    print(f"Kolom: {cols_train}")
    return x_train_cal, x_test_cal


def train_baseline(x_train_cal, y_train):
    """Latih model Regresi Linear hanya dengan fitur kalender."""
    model = LinearRegression()
    model.fit(x_train_cal, y_train.values.ravel())
    print("Model Regresi Linear berhasil dilatih.")
    return model


def evaluate_model(model, x_test_cal, y_test):
    """Hitung dan cetak metrik evaluasi."""
    y_pred = model.predict(x_test_cal)

    mae  = mean_absolute_error(y_test, y_pred)
    mse  = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    r2   = r2_score(y_test, y_pred)

    print("\n=== Evaluasi Model Baseline (Regresi Linear) ===")
    print(f"MAE  : {mae:.4f}")
    print(f"MSE  : {mse:.4f}")
    print(f"RMSE : {rmse:.4f}")
    print(f"R2   : {r2:.4f}")

    return y_pred, mae, mse, rmse, r2


def visualize_results(y_test, y_pred):
    """Visualisasi hasil prediksi vs aktual."""
    y_test_arr = np.array(y_test).flatten()
    y_pred_arr = np.array(y_pred).flatten()

    plt.figure(figsize=(8, 6))
    plt.scatter(y_test_arr, y_pred_arr, alpha=0.5, color='darkorange')
    mn = min(y_test_arr.min(), y_pred_arr.min())
    mx = max(y_test_arr.max(), y_pred_arr.max())
    plt.plot([mn, mx], [mn, mx], 'r--', linewidth=1.5)
    plt.xlabel('Actual Sales (2to5)')
    plt.ylabel('Predicted Sales (2to5)')
    plt.title('Baseline (Regresi Linear) — Actual vs Predicted\n(fitur kalender saja)')
    plt.tight_layout()
    plt.savefig("baseline_results.png", dpi=150)
    plt.show()
    print("Grafik disimpan: baseline_results.png")


def save_model(model, output_path):
    """Simpan model ke disk."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    joblib.dump(model, output_path)
    print(f"Model disimpan ke: {output_path}")


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

   
    preprocessed_dir = r"D:\Financial_Forecast\Data\Restaurant_source\Preprocessed_LSTM"
    model_output     = r"D:\Financial_Forecast\src\models\Baseline_model.joblib"
   
    x_train, x_test, y_train, y_test = load_data(preprocessed_dir)

    x_train_cal, x_test_cal = filter_calendar_features(x_train, x_test)

    model = train_baseline(x_train_cal, y_train)
    y_pred, *metrics = evaluate_model(model, x_test_cal, y_test)
    visualize_results(y_test, y_pred)
    save_model(model, model_output)
