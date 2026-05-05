# ==========================================================
# IMPACT MODULE - SECFAOS
# ==========================================================

from modules.carbon_model import get_carbon_intensity
from modules.optimization import get_tariff


def calculate_impact(future_df):

    energy_before = future_df["forecast_energy"].sum()
    energy_after = future_df["optimized_energy"].sum()

    cost_before = 0
    cost_after = 0
    carbon_before = 0
    carbon_after = 0

    for timestamp, row in future_df.iterrows():

        tariff = get_tariff(timestamp)
        carbon = get_carbon_intensity(timestamp)

        cost_before += row["forecast_energy"] * tariff
        cost_after += row["optimized_energy"] * tariff

        carbon_before += row["forecast_energy"] * carbon
        carbon_after += row["optimized_energy"] * carbon

    return {
        "energy_saved": energy_before - energy_after,
        "cost_saved": cost_before - cost_after,
        "carbon_saved": carbon_before - carbon_after
    }