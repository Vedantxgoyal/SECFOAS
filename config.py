# ==========================================================
# CONFIGURATION FILE - SECFAOS SYSTEM
# ==========================================================

import os

# ── Project root (auto-detected) ──────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Data settings ─────────────────────────────────────────
DATA_DIR          = os.path.join(BASE_DIR, "data")
METER_FILES = [
    "meter1_clean.csv",
    "meter2_clean.csv",
    "meter3_clean.csv",
    "meter4_clean.csv",
    "meter5_clean.csv",
    "meter6_clean.csv",
    "meter7_clean.csv",
    "meter8_clean.csv",
    "meter9_clean.csv",
    "meter10_clean.csv",
    "meter11_clean.csv",
]
MERGE_STRATEGY    = "concat"
DATA_PATH         = os.path.join(DATA_DIR, METER_FILES[0])  # legacy reference
TRAIN_SPLIT_RATIO = 0.8
TIME_FREQUENCY    = "30min"

# ── Inverse scaling ───────────────────────────────────────
# Assumed max consumption per 30-min slot in kWh
# Based on BSES 3-phase residential/small commercial meter specs
ENERGY_SCALE_KWH = 5.0

# ── Forecasting settings ──────────────────────────────────
SEASONAL_PERIOD   = 48
LSTM_UNITS_1      = 64
LSTM_UNITS_2      = 32
DENSE_UNITS       = 16
EPOCHS            = 30
BATCH_SIZE        = 32
VALIDATION_SPLIT  = 0.1

# ── Optimization settings ─────────────────────────────────
FLEXIBLE_LOAD_PERCENT     = 0.25
PEAK_PERCENTILE_THRESHOLD = 0.90
OPTIMIZATION_WEIGHT       = 0.5

# ── Tariff model (Time-of-Use) ────────────────────────────
NORMAL_TARIFF   = 8
PEAK_TARIFF     = 12
PEAK_START_HOUR = 18
PEAK_END_HOUR   = 22

# ── Device scheduling ─────────────────────────────────────
ENABLE_DEVICE_SCHEDULING = True   # toggle device LP on/off

# ── Carbon intensity model ────────────────────────────────
ENABLE_DYNAMIC_CARBON = True
CARBON_MEDIUM         = 0.82   # CEA national average kg CO2/kWh (v18, 2023)

# Legacy constants kept for reference — replaced by hourly profile in carbon_model.py
CARBON_LOW    = 0.68   # solar peak midday
CARBON_PEAK   = 0.93   # evening peak dispatch
CARBON_LATE   = 0.83   # late night baseload