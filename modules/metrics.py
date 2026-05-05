# ==========================================================
# METRICS MODULE - SECFAOS
# ==========================================================

def compute_peak_metrics(future_df):

    peak_before = future_df["forecast_energy"].max()
    peak_after = future_df["optimized_energy"].max()

    peak_reduction_percent = (
        (peak_before - peak_after) / peak_before * 100
        if peak_before != 0 else 0
    )

    return peak_before, peak_after, peak_reduction_percent


def compute_load_factor(future_df):

    avg_before = future_df["forecast_energy"].mean()
    peak_before = future_df["forecast_energy"].max()

    avg_after = future_df["optimized_energy"].mean()
    peak_after = future_df["optimized_energy"].max()

    lf_before = avg_before / peak_before if peak_before != 0 else 0
    lf_after = avg_after / peak_after if peak_after != 0 else 0

    improvement = (lf_after - lf_before) * 100

    return lf_before, lf_after, improvement


def compute_annual_projection(daily_savings, multiplier=365):
    return daily_savings * multiplier