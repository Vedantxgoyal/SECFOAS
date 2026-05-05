# ==========================================================
# PREPROCESSING MODULE - SECFAOS
# ==========================================================

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from statsmodels.tsa.stattools import adfuller
from config import TRAIN_SPLIT_RATIO


def split_train_test(df):
    """
    Splits dataframe into train and test sets by position.
    Always positional — never by date.
    Works correctly with multi-meter, multi-year merged data.
    """
    if df.empty:
        raise ValueError("Cannot split an empty dataframe.")

    split_index = int(len(df) * TRAIN_SPLIT_RATIO)

    if split_index == 0 or split_index == len(df):
        raise ValueError(f"TRAIN_SPLIT_RATIO={TRAIN_SPLIT_RATIO} produces empty train or test set.")

    train = df.iloc[:split_index]
    test = df.iloc[split_index:]

    print(f"  Split: train={len(train)} records | test={len(test)} records | "
          f"ratio={TRAIN_SPLIT_RATIO:.0%}/{1-TRAIN_SPLIT_RATIO:.0%}")

    return train, test


def perform_adf_test(series):
    """
    Augmented Dickey-Fuller test for stationarity.
    Drops NaNs before testing to avoid statsmodels errors.
    Returns dictionary of results.
    """
    clean = series.dropna()

    if len(clean) < 20:
        return {
            "ADF Statistic": None,
            "p-value": None,
            "Critical Values": None,
            "Is Stationary": None,
            "Error": "Insufficient data for ADF test (need at least 20 points)"
        }

    result = adfuller(clean)

    adf_result = {
        "ADF Statistic": round(result[0], 4),
        "p-value": round(result[1], 4),
        "Critical Values": {k: round(v, 4) for k, v in result[4].items()},
        "Is Stationary": result[1] < 0.05
    }

    print(f"  ADF Statistic : {adf_result['ADF Statistic']}")
    print(f"  p-value       : {adf_result['p-value']}")
    print(f"  Stationary    : {adf_result['Is Stationary']}")

    return adf_result


def scale_data(train, test):
    """
    Fits MinMaxScaler on training data only (no leakage).
    Transforms both train and test.
    Returns scaler (needed for inverse transform) + scaled arrays.
    """
    if len(train) == 0 or len(test) == 0:
        raise ValueError("Train or test set is empty. Cannot scale.")

    scaler = MinMaxScaler(feature_range=(0, 1))

    train_values = train.values.reshape(-1, 1) if hasattr(train, 'values') else np.array(train).reshape(-1, 1)
    test_values = test.values.reshape(-1, 1) if hasattr(test, 'values') else np.array(test).reshape(-1, 1)

    train_scaled = scaler.fit_transform(train_values)
    test_scaled = scaler.transform(test_values)

    print(f"  Scaler fitted  | train range: [{train_values.min():.4f}, {train_values.max():.4f}]")

    return scaler, train_scaled, test_scaled


def inverse_scale(scaler, values):
    """
    Converts scaled (0-1) values back to original units.
    Use this on any forecast or optimisation output to get real values.

    Args:
        scaler : fitted MinMaxScaler from scale_data()
        values : array-like of scaled values

    Returns:
        1D numpy array in original units
    """
    values = np.array(values).reshape(-1, 1)
    return scaler.inverse_transform(values).flatten()

def to_kwh(normalised_values, scale=None):
    """
    Converts normalised 0-1 index to approximate kWh.
    Uses ENERGY_SCALE_KWH from config as the assumed maximum.
    """
    from config import ENERGY_SCALE_KWH
    if scale is None:
        scale = ENERGY_SCALE_KWH
    return np.array(normalised_values) * scale