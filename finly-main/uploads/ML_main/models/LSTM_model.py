import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau


def data(preprocessed_dir="Data/Restaurant/Preprocessed_LSTM"):
    """Load data hasil preprocessing LSTM."""
    x_train = pd.read_csv(f"{preprocessed_dir}/x_train.csv")
    x_test  = pd.read_csv(f"{preprocessed_dir}/x_test.csv")
    y_train = pd.read_csv(f"{preprocessed_dir}/y_train.csv")
    y_test  = pd.read_csv(f"{preprocessed_dir}/y_test.csv")

    print("Shape x_train:", x_train.shape)
    print("Shape x_test :", x_test.shape)
    print("Shape y_train:", y_train.shape)
    print("Shape y_test :", y_test.shape)

    return x_train, x_test, y_train, y_test


def sequence_data(x, y, time_steps=14):
    """
    Buat sequence 3D untuk LSTM: (samples, time_steps, features).
    - x          : DataFrame fitur
    - y          : Series/DataFrame target
    - time_steps : panjang jendela waktu
    """
    Xs, Ys = [], []
    for i in range(len(x) - time_steps):
        Xs.append(x.iloc[i:(i + time_steps)].values)
        Ys.append(y.iloc[i + time_steps].values)
    return np.array(Xs), np.array(Ys)


def build_model(input_shape):
    """
    Bangun model LSTM 3 layer.
    - input_shape : (time_steps, n_features)
    """
    model = Sequential([
        LSTM(128, return_sequences=True, input_shape=input_shape),
        Dropout(0.2),
        LSTM(64, return_sequences=False),
        Dropout(0.2),
        Dense(32, activation='relu'),
        Dense(1)
    ])

    model.compile(
        optimizer='adam',
        loss='mean_squared_error'
    )
    model.summary()
    return model


def training(model, X_train, y_train, X_test, y_test, epochs=10, batch_size=16):

    # Hentikan training otomatis saat val_loss tidak membaik
    early_stop = EarlyStopping(
        monitor='val_loss',
        patience=25,
        restore_best_weights=True,
        verbose=1
    )

    # Turunkan learning rate otomatis saat val_loss stagnan
    reduce_lr = ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,
        patience=10,
        min_lr=1e-6,
        verbose=1
    )

    """Latih model dan kembalikan history training."""
    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=[early_stop, reduce_lr],
        verbose=1
    )
    return history


def evaluate_model(model, X_test, y_test):
    """Hitung dan cetak metrik evaluasi."""
    y_pred = model.predict(X_test)

    mae  = mean_absolute_error(y_test, y_pred)
    mse  = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    r2   = r2_score(y_test, y_pred)

    print("\n=== Evaluasi Model LSTM ===")
    print(f"MAE  : {mae:.4f}")
    print(f"MSE  : {mse:.4f}")
    print(f"RMSE : {rmse:.4f}")
    print(f"R2   : {r2:.4f}")

    return y_pred, mae, mse, rmse, r2


def visualize_results(y_test, y_pred, history=None):
    """Visualisasi hasil prediksi vs aktual dan loss curve training."""
    fig, axes = plt.subplots(1, 2 if history is not None else 1, figsize=(14, 5))

    # Plot prediksi vs aktual
    ax1 = axes[0] if history is not None else axes
    ax1.scatter(y_test, y_pred, alpha=0.5, color='steelblue')
    mn = min(y_test.min(), y_pred.min())
    mx = max(y_test.max(), y_pred.max())
    ax1.plot([mn, mx], [mn, mx], 'r--', linewidth=1.5)
    ax1.set_xlabel('Actual Sales (2to5)')
    ax1.set_ylabel('Predicted Sales (2to5)')
    ax1.set_title('LSTM – Actual vs Predicted')

    # Plot loss curve
    if history is not None:
        ax2 = axes[1]
        ax2.plot(history.history['loss'],     label='Train Loss')
        ax2.plot(history.history['val_loss'], label='Val Loss')
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('MSE Loss')
        ax2.set_title('Training & Validation Loss')
        ax2.legend()

    plt.tight_layout()
    plt.savefig("lstm_results.png", dpi=150)
    plt.show()
    print("Grafik disimpan: lstm_results.png")


def save_model(model, output_path="src/models/LSTM_model.keras"):
    """Simpan model ke disk."""
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    model.save(output_path)
    print(f"Model disimpan ke: {output_path}")


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    preprocessed_dir = r"D:\Financial_Forecast\Data\Restaurant_source\Preprocessed_LSTM"
    model_output     = r"D:\Financial_Forecast\src\models\LSTM_model.keras"

    TIME_STEPS = 21   # panjang jendela waktu (hari)
    EPOCHS     = 10
    BATCH_SIZE = 16

    # 1. Load data
    x_train, x_test, y_train, y_test = data(preprocessed_dir)

    # 2. Buat sequence 3D untuk LSTM
    X_train_seq, y_train_seq = sequence_data(x_train, y_train, TIME_STEPS)
    X_test_seq,  y_test_seq  = sequence_data(x_test,  y_test,  TIME_STEPS)

    print(f"\nShape setelah sequence – X_train: {X_train_seq.shape}, X_test: {X_test_seq.shape}")

    # 3. Bangun & latih model
    model   = build_model((X_train_seq.shape[1], X_train_seq.shape[2]))
    history = training(model, X_train_seq, y_train_seq, X_test_seq, y_test_seq, EPOCHS, BATCH_SIZE)

    # 4. Evaluasi
    y_pred, *metrics = evaluate_model(model, X_test_seq, y_test_seq)

    # 5. Visualisasi
    visualize_results(y_test_seq.flatten(), y_pred.flatten(), history)

    # 6. Simpan model
    save_model(model, model_output)
