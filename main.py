# ==========================================================
# MAIN ORCHESTRATION FILE - SECFAOS SYSTEM
# ==========================================================

import os
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"]  = "3"

import logging
import numpy as np
import pandas as pd
from datetime import timedelta

from modules.data_loader    import load_data
from modules.preprocessing  import split_train_test, perform_adf_test, scale_data
from modules.forecasting    import naive_forecast, sarima_grid_search, lstm_grid_search
from modules.optimization   import optimize_forecast
from modules.impact         import calculate_impact
from modules.metrics        import compute_peak_metrics, compute_load_factor, compute_annual_projection
from modules.visualization  import (
    plot_forecast,
    plot_optimization,
    plot_energy_heatmap,
    plot_peak_shaving_bars,
    plot_cost_breakdown,
    plot_train_test_split,
    plot_daily_pattern,
    plot_weekly_overview,
)
from config import SEASONAL_PERIOD, METER_FILES, DATA_DIR

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Blending weights — LSTM anchor + historical shape
LSTM_WEIGHT    = 0.40
PROFILE_WEIGHT = 0.60


# ==========================================================
# HISTORICAL PROFILE BUILDER
# ==========================================================

def _build_historical_profile(df: pd.DataFrame, forecast_index: pd.DatetimeIndex) -> np.ndarray:
    """
    Builds a 48-slot daily profile from the most recent same-DOW days.
    Fallback chain:
      1. Last 4 complete same-DOW days
      2. Most recent complete day (any DOW)
      3. Overall 30-min slot mean
    """
    forecast_dow  = forecast_index[0].dayofweek
    same_dow_days = []

    for date, group in df.groupby(df.index.date):
        if (pd.Timestamp(date).dayofweek == forecast_dow
                and len(group) == SEASONAL_PERIOD):
            same_dow_days.append(group["energy"].values)

    if len(same_dow_days) >= 2:
        recent  = same_dow_days[-4:]
        profile = np.mean(recent, axis=0)
        logger.info("Historical profile: %d same-DOW days mean=%.4f std=%.4f",
                    len(recent), profile.mean(), profile.std())
        return profile

    for date, group in reversed(list(df.groupby(df.index.date))):
        if len(group) == SEASONAL_PERIOD:
            logger.warning("Using most recent complete day (%s) as profile.", date)
            return group["energy"].values

    logger.warning("Using overall 30-min slot mean as profile fallback.")
    overall = df.groupby(df.index.time)["energy"].mean()
    return np.array([overall.get(ts.time(), df["energy"].mean()) for ts in forecast_index])


# ==========================================================
# FUTURE FORECAST — BLENDED LSTM + HISTORICAL PROFILE
# ==========================================================

def generate_future_forecast_lstm(
    df:     pd.DataFrame,
    result: dict,
    scaler,
) -> pd.DataFrame:
    """
    Generates 48-slot forecast using direct multi-output LSTM
    blended with historical same-DOW profile.

    Strategy: LSTM_WEIGHT * lstm_direct + PROFILE_WEIGHT * hist_profile
    - LSTM provides learned consumption level anchor
    - Historical profile provides realistic intraday shape
    - Blending prevents flat forecast when LSTM over-averages
    """
    seq_len      = result["config"]["seq_len"]
    direct_model = result.get("direct_model")

    if direct_model is None:
        raise RuntimeError(
            "direct_model missing in lstm result. "
            "Re-run lstm_grid_search with updated forecasting.py."
        )

    # ── Forecast index ────────────────────────────────────────────────────
    forecast_start = df.index[-1] + timedelta(minutes=30)
    future_index   = pd.date_range(
        start=forecast_start, periods=SEASONAL_PERIOD, freq="30min"
    )

    # ── Historical profile ────────────────────────────────────────────────
    hist_profile = _build_historical_profile(df, future_index)

    # ── Seed selection: most recent complete same-DOW day ─────────────────
    forecast_dow = future_index[0].dayofweek
    seed_values  = None

    for date, group in reversed(list(df.groupby(df.index.date))):
        if (pd.Timestamp(date).dayofweek == forecast_dow
                and len(group) == SEASONAL_PERIOD):
            seed_values = group["energy"].values[-seq_len:]
            logger.info("Seed: same-DOW date=%s mean=%.4f", date, seed_values.mean())
            break

    if seed_values is None:
        seed_values = df["energy"].values[-seq_len:]
        logger.warning("No complete same-DOW day found. Using tail of df as seed.")

    # ── LSTM forward pass ─────────────────────────────────────────────────
    seed_scaled = scaler.transform(seed_values.reshape(-1, 1))
    X_input     = seed_scaled.reshape(1, seq_len, 1).astype(np.float32)

    pred_scaled = direct_model(X_input, training=False).numpy()
    preds_lstm  = scaler.inverse_transform(pred_scaled.reshape(-1, 1)).flatten()
    preds_lstm  = np.clip(preds_lstm, 0, None)

    # ── Blend ─────────────────────────────────────────────────────────────
    blended = LSTM_WEIGHT * preds_lstm + PROFILE_WEIGHT * hist_profile
    blended = np.clip(blended, 0, None)

    # ── Diagnostics ───────────────────────────────────────────────────────
    print(f"\nForecast Components:")
    print(f"  LSTM (direct) — mean={preds_lstm.mean():.4f}  "
          f"std={preds_lstm.std():.4f}  max={preds_lstm.max():.4f}")
    print(f"  Hist profile  — mean={hist_profile.mean():.4f}  "
          f"std={hist_profile.std():.4f}  max={hist_profile.max():.4f}")
    print(f"  Blended       — mean={blended.mean():.4f}  "
          f"std={blended.std():.4f}  max={blended.max():.4f}")
    print(f"  Strategy      — {LSTM_WEIGHT:.0%} LSTM + {PROFILE_WEIGHT:.0%} historical profile")

    return pd.DataFrame({"forecast_energy": blended}, index=future_index)


# ==========================================================
# MAIN PIPELINE
# ==========================================================

def main():

    print("==========================================")
    print(" SECFAOS - Smart Energy Optimization System")
    print("==========================================\n")

    # ── Load & Merge all meters ───────────────────────────────────────────
    print("----- LOADING METERS -----")
    df = load_data()

    # Variance check immediately after load
    std_check = df["energy"].std()
    print(f"  Variance check: std={std_check:.4f} — "
          f"{'OK' if std_check > 0.05 else 'WARNING: low variance — check meter files'}")

    train, test = split_train_test(df)

    # ── Stationarity ──────────────────────────────────────────────────────
    adf_results = perform_adf_test(train["energy"])
    print("ADF Stationary:", adf_results["Is Stationary"])

    # ── Scaling ───────────────────────────────────────────────────────────
    scaler, _, _ = scale_data(train["energy"], test["energy"])

    # ── Combined Meter Summary ────────────────────────────────────────────
    total_consumption = df["energy"].sum()
    avg_daily         = df["energy"].resample("D").sum().mean()
    max_slot          = df["energy"].max()
    min_slot          = df["energy"].min()

    print(f"\n----- COMBINED METER SUMMARY -----")
    print(f"Meters configured:         {len(METER_FILES)}")
    print(f"Data directory:            {DATA_DIR}")
    print(f"Data Period:               {df.index[0].date()} to {df.index[-1].date()}")
    print(f"Total Records:             {len(df)}")
    print(f"Std (variance check):      {round(std_check, 4)}")
    print(f"Total Consumption (index): {round(total_consumption, 4)}")
    print(f"Average Daily Consumption: {round(avg_daily, 4)} units/day")
    print(f"Peak Slot Consumption:     {round(max_slot, 4)}")
    print(f"Min Slot Consumption:      {round(min_slot, 4)}")

    # ── EDA Plots ─────────────────────────────────────────────────────────
    print("\nGenerating EDA plots...")
    plot_train_test_split(train, test)
    plot_daily_pattern(df)
    plot_weekly_overview(df)
    plot_energy_heatmap(df)

    # ── Baseline ──────────────────────────────────────────────────────────
    print("\n----- BASELINE -----")
    naive_result = naive_forecast(train, test)
    print("Naive MAE: ", round(naive_result["mae"],  4))
    print("Naive RMSE:", round(naive_result["rmse"], 4))

    # ── SARIMA ────────────────────────────────────────────────────────────
    print("\n----- SARIMA GRID SEARCH -----")
    sarima_result = None
    sarima_failed = False
    try:
        sarima_result = sarima_grid_search(train, test)
        print("Best SARIMA Order:   ", sarima_result["order"])
        print("Best Seasonal Order: ", sarima_result["seasonal_order"])
        print("Best SARIMA MAE:     ", round(sarima_result["mae"],  4))
        print("Best SARIMA RMSE:    ", round(sarima_result["rmse"], 4))
    except RuntimeError as e:
        logger.error("SARIMA failed: %s", e)
        sarima_failed = True

    # ── LSTM ──────────────────────────────────────────────────────────────
    print("\n----- LSTM GRID SEARCH -----")
    lstm_result = None
    lstm_failed = False
    try:
        lstm_result = lstm_grid_search(train["energy"], test["energy"], scaler, force_retrain=False)
        print("Best LSTM Config:", lstm_result["config"])
        print("Best LSTM MAE:   ", round(lstm_result["mae"], 4))
    except RuntimeError as e:
        logger.error("LSTM failed: %s", e)
        lstm_failed = True

    # ── Model Comparison Plot ─────────────────────────────────────────────
    if not sarima_failed and not lstm_failed:
        sarima_preds = sarima_result["forecast"].values
        lstm_preds   = lstm_result["predictions"]
        min_len      = min(len(sarima_preds), len(lstm_preds), len(test))
        plot_forecast(
            test_index     = test.index[:min_len],
            actual         = test["energy"].values[:min_len],
            sarima_pred    = sarima_preds[:min_len],
            lstm_pred      = lstm_preds[:min_len],
            sarima_mae     = sarima_result["mae"],
            lstm_mae       = lstm_result["mae"],
            selected_model = "LSTM" if lstm_result["mae"] <= sarima_result["mae"] else "SARIMA",
        )

    # ── Model Selection ───────────────────────────────────────────────────
    if lstm_failed and sarima_failed:
        logger.error("Both models failed — falling back to naive forecast.")
        print("\nSelected Model: NAIVE (fallback)")
        selected_model_type = "NAIVE"
        selected_model      = None
    elif sarima_failed or (
        not lstm_failed and lstm_result["mae"] <= sarima_result["mae"]
    ):
        selected_model_type = "LSTM"
        selected_model      = lstm_result
    else:
        selected_model_type = "SARIMA"
        selected_model      = sarima_result

    print("\nSelected Model:", selected_model_type)

    # ── Future Forecast ───────────────────────────────────────────────────
    print("\nGenerating future forecast...")

    if selected_model_type == "LSTM":
        future_df = generate_future_forecast_lstm(df, selected_model, scaler)

    elif selected_model_type == "SARIMA":
        future_values = selected_model["model"].forecast(steps=SEASONAL_PERIOD)
        future_index  = pd.date_range(
            start=df.index[-1] + timedelta(minutes=30),
            periods=SEASONAL_PERIOD, freq="30min",
        )
        future_df = pd.DataFrame(
            {"forecast_energy": future_values.values}, index=future_index
        )

    else:
        future_index = pd.date_range(
            start=df.index[-1] + timedelta(minutes=30),
            periods=SEASONAL_PERIOD, freq="30min",
        )
        hist_profile = _build_historical_profile(df, future_index)
        future_df    = pd.DataFrame(
            {"forecast_energy": hist_profile}, index=future_index
        )

    print("\nFuture Forecast Sample:")
    print(future_df.head(8))

    # ── Forecast Diagnostics ──────────────────────────────────────────────
    f_std  = future_df["forecast_energy"].std()
    f_mean = future_df["forecast_energy"].mean()
    f_min  = future_df["forecast_energy"].min()
    f_max  = future_df["forecast_energy"].max()

    print(f"\nForecast Diagnostics:")
    print(f"  mean={round(f_mean,4)}  std={round(f_std,4)}"
          f"  min={round(f_min,4)}  max={round(f_max,4)}")

    if f_std < 0.02:
        print("  WARNING: std is very low — forecast curve may be flat.")
    elif f_std > 0.15:
        print("  WARNING: std is very high — forecast may be noisy.")
    else:
        print("  Shape OK — realistic daily variation detected.")

    # ── Optimization ──────────────────────────────────────────────────────
    optimized_df = optimize_forecast(future_df)

    # ── Impact ────────────────────────────────────────────────────────────
    impact                                      = calculate_impact(optimized_df)
    peak_before, peak_after, peak_reduction_pct = compute_peak_metrics(optimized_df)
    lf_before,   lf_after,   lf_improvement     = compute_load_factor(optimized_df)
    annual_cost                                 = compute_annual_projection(impact["cost_saved"])
    annual_carbon                               = compute_annual_projection(impact["carbon_saved"])

   # ── Executive Summary ─────────────────────────────────────────────────
    from config import ENERGY_SCALE_KWH
    from modules.preprocessing import to_kwh

    energy_saved_kwh = to_kwh(impact["energy_saved"])
    peak_before_kwh  = to_kwh(peak_before)
    peak_after_kwh   = to_kwh(peak_after)

    print("\n==========================================")
    print(" OPTIMIZATION IMPACT SUMMARY")
    print("==========================================")
    print(f"Energy Saved:          {round(impact['energy_saved'], 4)} units  "
          f"({round(energy_saved_kwh, 3)} kWh approx)")
    print(f"Cost Saved (Rs):       {round(impact['cost_saved'], 2)}")
    print(f"Carbon Saved (kg CO2): {round(impact['carbon_saved'], 4)}")
    print("\n----- PEAK METRICS -----")
    print(f"Peak Before:           {round(peak_before, 4)} units  "
          f"({round(peak_before_kwh, 3)} kWh approx)")
    print(f"Peak After:            {round(peak_after, 4)} units  "
          f"({round(peak_after_kwh, 3)} kWh approx)")
    print(f"Peak Reduction (%):    {round(peak_reduction_pct, 2)}")
    print("\n----- LOAD FACTOR -----")
    print(f"Before:                {round(lf_before, 4)}")
    print(f"After:                 {round(lf_after, 4)}")
    print(f"Improvement (%):       {round(lf_improvement, 2)}")
    print("\n----- ANNUAL PROJECTION -----")
    print(f"Annual Cost Saving (Rs):          {round(annual_cost, 2)}")
    print(f"Annual Carbon Reduction (kg CO2): {round(annual_carbon, 2)}")
    print(f"\nNote: kWh values are approximate (scale factor = {ENERGY_SCALE_KWH} kWh/slot max)")

    # ── Optimization Plots ────────────────────────────────────────────────
    selected_mae = selected_model["mae"] if selected_model and "mae" in selected_model else None
    plot_optimization(optimized_df, mae=selected_mae, selected_model=selected_model_type)
    plot_peak_shaving_bars(optimized_df)
    plot_cost_breakdown(optimized_df)

    print("\nSystem Execution Complete.")
    print("\nPlots saved:")
    for name in [
        "output_train_test_split.png",
        "output_daily_pattern.png",
        "output_weekly_overview.png",
        "output_heatmap.png",
        "output_forecast_comparison.png",
        "output_optimization.png",
        "output_peak_shaving_bars.png",
        "output_cost_breakdown.png",
    ]:
        print(f"  {name}")


if __name__ == "__main__":
    main()