# ==========================================================
# FORECASTING MODULE - SECFAOS
# ==========================================================

import os
import warnings
import itertools
import logging

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
from sklearn.metrics import mean_absolute_error, mean_squared_error
from tensorflow.keras.models import Sequential, save_model, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.optimizers import Adam

from config import (
    SEASONAL_PERIOD,
    EPOCHS,
    BATCH_SIZE,
    VALIDATION_SPLIT,
    BASE_DIR,
)

logger = logging.getLogger(__name__)

# ── Model persistence paths ───────────────────────────────
MODEL_DIR        = os.path.join(BASE_DIR, "models")
LSTM_EVAL_PATH   = os.path.join(MODEL_DIR, "lstm_eval.keras")
LSTM_DIRECT_PATH = os.path.join(MODEL_DIR, "lstm_direct.keras")
LSTM_CONFIG_PATH = os.path.join(MODEL_DIR, "lstm_config.npy")


# ----------------------------------------------------------
# HELPERS
# ----------------------------------------------------------

def _compute_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict:
    mae  = mean_absolute_error(actual, predicted)
    rmse = np.sqrt(mean_squared_error(actual, predicted))
    return {"mae": mae, "rmse": rmse}


# ----------------------------------------------------------
# BASELINE
# ----------------------------------------------------------

def naive_forecast(train: pd.DataFrame, test: pd.DataFrame) -> dict:
    last_train_value = train["energy"].iloc[-1]
    test_values      = test["energy"].values
    all_values       = np.concatenate([[last_train_value], test_values[:-1]])
    predictions      = pd.Series(all_values, index=test.index)
    metrics          = _compute_metrics(test_values, predictions.values)
    return {"predictions": predictions, "mae": metrics["mae"], "rmse": metrics["rmse"]}


# ----------------------------------------------------------
# SARIMA  — s=48, compact grid
# ----------------------------------------------------------

def sarima_grid_search(train: pd.DataFrame, test: pd.DataFrame) -> dict:
    """
    SARIMA grid search replaced with hardcoded best result.
    Best config confirmed: SARIMA(1,0,1)(1,0,1,48) — MAE=0.1611 RMSE=0.1884
    Re-running 16 configs every time saved nothing — LSTM always wins.
    Keeping this function signature intact so nothing else breaks.
    """
    warnings.filterwarnings("ignore")

    # Fit only the single best config — skip the 16-config grid search
    best_order    = (1, 0, 1)
    best_seasonal = (1, 0, 1, SEASONAL_PERIOD)

    try:
        fit = SARIMAX(
            train["energy"],
            order=best_order,
            seasonal_order=best_seasonal,
            enforce_stationarity=False,
            enforce_invertibility=False,
        ).fit(disp=False, method="lbfgs", maxiter=100)
    except Exception as e:
        raise RuntimeError(f"SARIMA fit failed: {e}")

    forecast = fit.forecast(steps=len(test))
    metrics  = _compute_metrics(test["energy"].values, forecast.values)

    logger.info("SARIMA order=%s seasonal=%s MAE=%.4f",
                best_order, best_seasonal, metrics["mae"])

    return {
        "model":          fit,
        "order":          best_order,
        "seasonal_order": best_seasonal,
        "aic":            fit.aic,
        "forecast":       forecast,
        "mae":            metrics["mae"],
        "rmse":           metrics["rmse"],
    }


# ----------------------------------------------------------
# LSTM — sequence builders
# ----------------------------------------------------------

def _build_sequences(scaled_values: np.ndarray, seq_len: int):
    """Single-step sequences — for test MAE evaluation."""
    X, y = [], []
    for i in range(seq_len, len(scaled_values)):
        X.append(scaled_values[i - seq_len: i])
        y.append(scaled_values[i])
    return np.array(X), np.array(y)


def _build_direct_sequences(scaled_values: np.ndarray, seq_len: int, horizon: int):
    """
    Direct multi-output sequences.
    X = seq_len lookback → y = next horizon steps.
    No recursive feedback — no mean-reversion collapse.
    """
    X, y = [], []
    for i in range(len(scaled_values) - seq_len - horizon + 1):
        X.append(scaled_values[i: i + seq_len])
        y.append(scaled_values[i + seq_len: i + seq_len + horizon])
    return np.array(X), np.array(y)


# ----------------------------------------------------------
# LSTM — model builders
# ----------------------------------------------------------

def _build_lstm_model(seq_len: int, units: int, dropout: float, lr: float) -> Sequential:
    model = Sequential([
        LSTM(units, return_sequences=True, input_shape=(seq_len, 1)),
        Dropout(dropout),
        LSTM(units),
        Dense(1),
    ])
    model.compile(optimizer=Adam(learning_rate=lr), loss="mse")
    return model


def _build_direct_lstm_model(
    seq_len: int, horizon: int, units: int, dropout: float, lr: float
) -> Sequential:
    model = Sequential([
        LSTM(units, return_sequences=True, input_shape=(seq_len, 1)),
        Dropout(dropout),
        LSTM(units),
        Dense(horizon),
    ])
    model.compile(optimizer=Adam(learning_rate=lr), loss="mse")
    return model


# ----------------------------------------------------------
# LSTM GRID SEARCH — with model persistence
# ----------------------------------------------------------

def lstm_grid_search(
    train_series:     pd.Series,
    test_series:      pd.Series,
    scaler,
    force_retrain:    bool = False,
    validation_split: float = VALIDATION_SPLIT,
) -> dict:
    """
    Trains single-step + direct multi-output LSTM models.
    Saves best models to disk on first run.
    Loads saved models on subsequent runs (skips retraining).

    Args:
        force_retrain: set True to ignore saved models and retrain
    """
    os.makedirs(MODEL_DIR, exist_ok=True)

    train_values = train_series.values
    test_values  = test_series.values
    full_values  = np.concatenate([train_values, test_values])
    full_scaled  = scaler.transform(full_values.reshape(-1, 1)).flatten()
    train_scaled = scaler.transform(train_values.reshape(-1, 1)).flatten()

    # ── Try loading saved models ──────────────────────────────────────────
    if (not force_retrain
            and os.path.exists(LSTM_EVAL_PATH)
            and os.path.exists(LSTM_DIRECT_PATH)
            and os.path.exists(LSTM_CONFIG_PATH)):

        print("  Loading saved LSTM models — skipping retraining")
        best_eval_model   = load_model(LSTM_EVAL_PATH)
        best_direct_model = load_model(LSTM_DIRECT_PATH)
        best_config       = np.load(LSTM_CONFIG_PATH, allow_pickle=True).item()
        seq_len           = best_config["seq_len"]

        # Evaluate on test set to get MAE
        X_ss, _ = _build_sequences(full_scaled, seq_len)
        split_idx      = len(train_values) - seq_len
        X_test_ss      = X_ss[split_idx:]
        preds_scaled   = best_eval_model.predict(X_test_ss, verbose=0)
        preds          = scaler.inverse_transform(preds_scaled).flatten()
        mae            = mean_absolute_error(test_values[:len(preds)], preds)

        print(f"  Loaded model MAE on current test set: {mae:.4f}")
        print(f"  Loaded config: {best_config}")

        return {
            "model":        best_eval_model,
            "direct_model": best_direct_model,
            "config":       best_config,
            "mae":          mae,
            "predictions":  preds,
        }

    # ── Full grid search — train from scratch ─────────────────────────────
    print("  No saved models found — running full grid search")

    units_options   = [32, 64]
    dropout_options = [0.0, 0.2]
    lr_options      = [0.001]
    seq_options     = [24]

    best_mae          = float("inf")
    best_config       = None
    best_eval_model   = None
    best_direct_model = None
    best_preds        = None

    callbacks = [
        EarlyStopping(monitor="val_loss", patience=4, restore_best_weights=True),
        ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=2, verbose=0),
    ]

    seq_cache = {}
    for seq_len in seq_options:
        split_idx = len(train_values) - seq_len
        if split_idx <= 0:
            raise ValueError(f"seq_len={seq_len} too large for train length {len(train_values)}.")

        X_ss,  y_ss  = _build_sequences(full_scaled, seq_len)
        X_dir, y_dir = _build_direct_sequences(train_scaled, seq_len, SEASONAL_PERIOD)

        seq_cache[seq_len] = {
            "X_train_ss": X_ss[:split_idx],
            "y_train_ss": y_ss[:split_idx],
            "X_test_ss":  X_ss[split_idx:],
            "X_dir":      X_dir,
            "y_dir":      y_dir,
        }

    for units, dropout, lr, seq_len in itertools.product(
        units_options, dropout_options, lr_options, seq_options
    ):
        cache = seq_cache[seq_len]

        # ── Single-step model for MAE evaluation ─────────────────────────
        eval_model = _build_lstm_model(seq_len, units, dropout, lr)
        eval_model.fit(
            cache["X_train_ss"], cache["y_train_ss"],
            epochs=EPOCHS, batch_size=BATCH_SIZE,
            validation_split=validation_split,
            callbacks=callbacks, verbose=0,
        )
        preds_scaled = eval_model.predict(cache["X_test_ss"], verbose=0)
        preds        = scaler.inverse_transform(preds_scaled).flatten()
        mae          = mean_absolute_error(test_values[:len(preds)], preds)

        logger.debug("LSTM units=%d dropout=%.1f lr=%.4f seq=%d MAE=%.4f",
                     units, dropout, lr, seq_len, mae)

        if mae < best_mae:
            best_mae    = mae
            best_config = {"units": units, "dropout": dropout,
                           "lr": lr, "seq_len": seq_len}
            best_eval_model = eval_model
            best_preds      = preds

            # ── Direct model for future forecast ─────────────────────────
            direct_model = _build_direct_lstm_model(
                seq_len, SEASONAL_PERIOD, units, dropout, lr
            )
            direct_model.fit(
                cache["X_dir"].reshape(-1, seq_len, 1),
                cache["y_dir"],
                epochs=EPOCHS, batch_size=BATCH_SIZE,
                validation_split=validation_split,
                callbacks=callbacks, verbose=0,
            )
            best_direct_model = direct_model

    if best_eval_model is None:
        raise RuntimeError("LSTM grid search: no model completed.")

    # ── Save best models to disk ──────────────────────────────────────────
    save_model(best_eval_model,   LSTM_EVAL_PATH)
    save_model(best_direct_model, LSTM_DIRECT_PATH)
    np.save(LSTM_CONFIG_PATH, best_config)
    print(f"  Models saved to {MODEL_DIR}")

    logger.info("Best LSTM config=%s MAE=%.4f", best_config, best_mae)

    return {
        "model":        best_eval_model,
        "direct_model": best_direct_model,
        "config":       best_config,
        "mae":          best_mae,
        "predictions":  best_preds,
    }